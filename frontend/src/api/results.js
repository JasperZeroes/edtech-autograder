import { apiRequest } from "./client";

export function getStudentResult(submissionId) {
  return apiRequest(`/submissions/${submissionId}/result`);
}

export function getInstructorSubmissions(assignmentId) {
  return apiRequest(`/assignments/${assignmentId}/submissions`);
}

export function getInstructorResult(assignmentId, submissionId) {
  return apiRequest(
    `/assignments/${assignmentId}/submissions/${submissionId}/result`,
  );
}

export function requestAiFeedback(submissionId) {
  return apiRequest(`/submissions/${submissionId}/ai-feedback`, {
    method: "POST",
  });
}
