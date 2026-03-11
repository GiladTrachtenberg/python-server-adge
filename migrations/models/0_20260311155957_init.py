from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
    "id" UUID NOT NULL PRIMARY KEY,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "password_hash" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL
);
COMMENT ON TABLE "users" IS 'Registered user account.';
CREATE TABLE IF NOT EXISTS "jobs" (
    "id" UUID NOT NULL PRIMARY KEY,
    "status" VARCHAR(20) NOT NULL,
    "celery_task_id" VARCHAR(255),
    "minio_object_key" VARCHAR(512),
    "error_message" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL,
    "updated_at" TIMESTAMPTZ NOT NULL,
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "jobs"."status" IS 'PENDING: pending\nPROCESSING: processing\nCOMPLETED: completed\nFAILED: failed\nCANCELLED: cancelled';
COMMENT ON TABLE "jobs" IS 'Async processing job linked to a user.';
CREATE TABLE IF NOT EXISTS "refresh_tokens" (
    "id" UUID NOT NULL PRIMARY KEY,
    "token_hash" VARCHAR(255) NOT NULL,
    "family_id" UUID NOT NULL,
    "revoked" BOOL NOT NULL,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "refresh_tokens" IS 'Hashed refresh token with family-based rotation tracking.';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
