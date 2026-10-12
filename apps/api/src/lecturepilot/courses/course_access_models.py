from dataclasses import dataclass


@dataclass(frozen=True)
class CourseActorAccess:
    is_owner: bool
    is_enrolled: bool
    same_tenant: bool
