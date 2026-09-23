import { apiRequest } from "./client";

export function submitSolution(assignmentId, file) {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest(`/assignments/${assignmentId}/submissions`, {
    method: "POST",
    body: formData,
  });
}

export function listMySubmissions() {
  return apiRequest("/submissions/mine");
}

export function getSubmission(submissionId) {
  return apiRequest(`/submissions/${submissionId}`);
}
