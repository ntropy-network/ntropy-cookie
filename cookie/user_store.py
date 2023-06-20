import os

import discord
import sqlalchemy as sa
import sqlalchemy.orm as so


class Base(so.DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"

    id: so.Mapped[int] = so.mapped_column(sa.Integer, primary_key=True)
    discord_id: so.Mapped[str] = so.mapped_column(sa.String)
    cached_txs_json: so.Mapped[str | None]


class UserStore:
    def __init__(self) -> None:
        db_url = os.environ.get("SQLALCHEMY_DATABASE_URL")
        self._engine = sa.create_engine(db_url or "sqlite:///db.sqlite")
        self._session_maker = so.sessionmaker(self._engine)
        Base.metadata.create_all(self._engine)

    def update_user(self, user: User):
        with self._session_maker() as session:
            session.add(user)
            session.commit()
            session.refresh(user)

    def create_user(self, discord_id: str) -> User:
        with self._session_maker() as session:
            user = User(discord_id=discord_id)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def get_user_from_discord(
        self, discord_user: discord.user.BaseUser | discord.Member
    ) -> User | None:
        with self._session_maker() as session:
            statement = sa.select(User).filter(User.discord_id == str(discord_user.id))
            return session.scalar(statement)

    def delete_user(self, user: User):
        with self._session_maker() as session:
            session.delete(session.get(User, user.id))
            session.commit()
