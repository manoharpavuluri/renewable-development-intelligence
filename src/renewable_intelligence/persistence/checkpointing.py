from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Any


DEFAULT_SQLITE_PATH = Path(
    "data/runtime/"
    "investigation_checkpoints.sqlite"
)


def checkpoint_backend_name() -> str:

    return (
        os.environ.get(
            "RDI_CHECKPOINT_BACKEND",
            "sqlite",
        )
        .strip()
        .lower()
    )


def checkpoint_backend_description() -> str:

    backend = checkpoint_backend_name()

    if backend == "sqlite":

        path = Path(
            os.environ.get(
                "RDI_SQLITE_CHECKPOINT_PATH",
                str(
                    DEFAULT_SQLITE_PATH
                ),
            )
        )

        return (
            f"sqlite:{path}"
        )

    if backend == "postgres":

        return (
            "postgres"
        )

    return (
        f"unsupported:{backend}"
    )


def _env_true(
    name: str,
    *,
    default: bool = False,
) -> bool:

    raw = os.environ.get(
        name
    )

    if raw is None:
        return default

    return (
        raw.strip().lower()
        in {
            "1",
            "true",
            "yes",
            "y",
            "on",
        }
    )


@contextmanager
def open_checkpointer() -> Iterator[Any]:

    backend = checkpoint_backend_name()


    # ========================================================
    # Local development
    # ========================================================

    if backend == "sqlite":

        from langgraph.checkpoint.sqlite import (
            SqliteSaver,
        )

        checkpoint_path = Path(
            os.environ.get(
                "RDI_SQLITE_CHECKPOINT_PATH",
                str(
                    DEFAULT_SQLITE_PATH
                ),
            )
        )

        checkpoint_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with SqliteSaver.from_conn_string(
            str(
                checkpoint_path
            )
        ) as checkpointer:

            yield checkpointer

        return


    # ========================================================
    # Production-compatible PostgreSQL backend
    #
    # This code path does NOT provision PostgreSQL.
    # It only connects to a database supplied through
    # RDI_POSTGRES_URL.
    # ========================================================

    if backend == "postgres":

        postgres_url = os.environ.get(
            "RDI_POSTGRES_URL"
        )

        if not postgres_url:

            raise RuntimeError(
                "RDI_CHECKPOINT_BACKEND=postgres "
                "requires RDI_POSTGRES_URL."
            )


        try:

            from langgraph.checkpoint.postgres import (
                PostgresSaver,
            )

        except ImportError as exc:

            raise RuntimeError(
                "PostgreSQL checkpoint support requires "
                "the langgraph-checkpoint-postgres "
                "package."
            ) from exc


        with PostgresSaver.from_conn_string(
            postgres_url
        ) as checkpointer:

            # Schema creation/migrations should normally
            # be performed deliberately during deployment.
            #
            # This flag is convenient for a first controlled
            # environment setup but defaults OFF.
            if _env_true(
                "RDI_POSTGRES_AUTO_SETUP"
            ):

                checkpointer.setup()


            yield checkpointer

        return


    raise ValueError(
        "Unsupported RDI_CHECKPOINT_BACKEND: "
        f"{backend!r}. Expected 'sqlite' "
        "or 'postgres'."
    )
