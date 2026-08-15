from taskflow.db import SessionLocal
from taskflow.models import Notification as NotificationModel
from taskflow.models import Project as ProjectModel
from taskflow.models import Task as TaskModel
from taskflow.models import User as UserModel


def create_status_change_notifications(
    task_id: str,
    old_status: str,
    new_status: str,
) -> int:
    with SessionLocal() as session:
        task = session.get(TaskModel, task_id)
        if task is None:
            return 0
        project = session.get(ProjectModel, task.project_id)
        recipients: set[str] = set()
        if project is not None:
            recipients.add(str(project.owner_id))
        if task.assignee:
            assignee = (
                session.query(UserModel)
                .filter(UserModel.username == task.assignee)
                .first()
            )
            if assignee is not None:
                recipients.add(assignee.id)
        if not recipients:
            return 0
        message = (
            f"Task '{task.title}' status changed from '{old_status}' to '{new_status}'"
        )
        session.add_all(
            NotificationModel(
                user_id=recipient,
                task_id=task_id,
                message=message,
            )
            for recipient in recipients
        )
        session.commit()
        return len(recipients)


def list_notifications_for_user(user_id: str) -> list[NotificationModel]:
    with SessionLocal() as session:
        return (
            session.query(NotificationModel)
            .filter(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.created_at, NotificationModel.id)
            .all()
        )


def clear_notifications() -> None:
    with SessionLocal() as session:
        session.query(NotificationModel).delete()
        session.commit()