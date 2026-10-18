"""Request body shared by the admin hide routes (feedback, ratings, scores). Layer 2."""

from pydantic import BaseModel, StrictBool


class HiddenFlagIn(BaseModel):
    is_hidden: StrictBool
