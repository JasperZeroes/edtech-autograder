import { apiRequest } from "./client";

export function listInstructorAssignments() {
  return apiRequest("/assignments/mine");
}

export function createAssignment(payload) {
  return apiRequest("/assignments", {
    method: "POST",
    body: payload,
  });
}

export function configureAssignment(assignmentId, payload) {
  return apiRequest(`/assignments/${assignmentId}/configuration`, {
    method: "PATCH",
    body: payload,
  });
}

export function publishAssignment(assignmentId) {
  return apiRequest(`/assignments/${assignmentId}/publish`, {
    method: "POST",
  });
}

export function unpublishAssignment(assignmentId) {
  return apiRequest(`/assignments/${assignmentId}/unpublish`, {
    method: "POST",
  });
}

export function listPublishedAssignments() {
  return apiRequest("/assignments");
}

export function getPublishedAssignment(assignmentId) {
  return apiRequest(`/assignments/${assignmentId}`);
}
