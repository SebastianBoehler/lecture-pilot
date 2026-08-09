export function quizAttemptResponse(init?: RequestInit) {
  const request = JSON.parse(String(init?.body));
  const correct =
    (request.block_id === "losses-and-risks-quiz" && request.option_index === 1) ||
    (request.block_id === "risk-threshold-check" && request.option_index === 0);
  return {
    block_id: request.block_id,
    component_id: request.block_id,
    selected_index: request.option_index,
    correct,
    attempt_index: 1,
    first_attempt_correct: correct,
    latest_outcome: correct ? "correct" : "incorrect",
    correction_state: correct ? "not_needed" : "needed",
    feedback: correct ? "Correct." : "Review and try a correction.",
  };
}
