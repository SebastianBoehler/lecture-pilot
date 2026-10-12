class LearningDesignError(ValueError):
    pass


class LearningDesignStaleError(LearningDesignError):
    pass


class LearningDesignUnavailableError(LearningDesignError):
    pass


class LearningDesignApprovalRequiredError(LearningDesignError):
    pass
