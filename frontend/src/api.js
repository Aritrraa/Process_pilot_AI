const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

function getHeaders(isJson = true) {
  const token = localStorage.getItem('token');
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (isJson) headers['Content-Type'] = 'application/json';
  return headers;
}

async function handleResponse(res) {
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // Auth
  login: (email, password) =>
    fetch(`${BASE_URL}/auth/login`, { method: 'POST', headers: getHeaders(), body: JSON.stringify({ email, password }) }).then(handleResponse),

  register: (email, password, full_name = null, role = 'Employee', department_id = null, manager_id = null) =>
    fetch(`${BASE_URL}/auth/register`, { 
      method: 'POST', 
      headers: getHeaders(), 
      body: JSON.stringify({ email, password, full_name, role, department_id, manager_id }) 
    }).then(handleResponse),

  getMe: () =>
    fetch(`${BASE_URL}/auth/me`, { headers: getHeaders() }).then(handleResponse),

  getDepartments: () =>
    fetch(`${BASE_URL}/auth/departments`, { headers: getHeaders() }).then(handleResponse),

  getManagers: () =>
    fetch(`${BASE_URL}/auth/managers`, { headers: getHeaders() }).then(handleResponse),

  getTeam: () =>
    fetch(`${BASE_URL}/auth/team`, { headers: getHeaders() }).then(handleResponse),

  transferEmployee: (employeeId, managerId) =>
    fetch(`${BASE_URL}/auth/employees/${employeeId}/transfer`, {
      method: 'PATCH',
      headers: getHeaders(),
      body: JSON.stringify({ manager_id: managerId })
    }).then(handleResponse),

  selectManager: (managerId) =>
    fetch(`${BASE_URL}/auth/select-manager`, {
      method: 'PATCH',
      headers: getHeaders(),
      body: JSON.stringify({ manager_id: managerId })
    }).then(handleResponse),

  // Documents
  uploadDocument: (file, departmentId) => {
    const formData = new FormData();
    formData.append('file', file);
    if (departmentId) formData.append('department_id', departmentId);
    return fetch(`${BASE_URL}/documents/upload`, { method: 'POST', headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }, body: formData }).then(handleResponse);
  },

  getDocuments: () =>
    fetch(`${BASE_URL}/documents/`, { headers: getHeaders() }).then(handleResponse),

  deleteDocument: (id) =>
    fetch(`${BASE_URL}/documents/${id}`, { method: 'DELETE', headers: getHeaders() }).then(handleResponse),

  // Chat
  chat: (message) =>
    fetch(`${BASE_URL}/chat/`, { method: 'POST', headers: getHeaders(), body: JSON.stringify({ message }) }).then(handleResponse),

  // Meetings
  getMeetings: () =>
    fetch(`${BASE_URL}/meetings/`, { headers: getHeaders() }).then(handleResponse),

  createMeeting: (title, transcript, meetingLink = null) =>
    fetch(`${BASE_URL}/meetings/`, { method: 'POST', headers: getHeaders(), body: JSON.stringify({ title, transcript, meeting_link: meetingLink }) }).then(handleResponse),

  // Tasks
  getTasks: () =>
    fetch(`${BASE_URL}/tasks/`, { headers: getHeaders() }).then(handleResponse),

  createTask: (title, description, assignedTo = null, documentId = null, meetingId = null) =>
    fetch(`${BASE_URL}/tasks/`, { 
      method: 'POST', 
      headers: getHeaders(), 
      body: JSON.stringify({ title, description, assigned_to: assignedTo, document_id: documentId, meeting_id: meetingId }) 
    }).then(handleResponse),

  updateTask: (id, status = null, assignedTo = null) => {
    const body = {};
    if (status !== null) body.status = status;
    if (assignedTo !== null) body.assigned_to = assignedTo;
    return fetch(`${BASE_URL}/tasks/${id}`, { 
      method: 'PATCH', 
      headers: getHeaders(), 
      body: JSON.stringify(body) 
    }).then(handleResponse);
  },

  // Settings
  getSettings: () =>
    fetch(`${BASE_URL}/settings/`, { headers: getHeaders() }).then(handleResponse),

  updateSettings: (gemini_api_key, groq_api_key, openai_api_key, llm_provider, system_prompt) =>
    fetch(`${BASE_URL}/settings/`, { method: 'PUT', headers: getHeaders(), body: JSON.stringify({ gemini_api_key, groq_api_key, openai_api_key, llm_provider, system_prompt }) }).then(handleResponse),

  // Analytics
  getAnalytics: () =>
    fetch(`${BASE_URL}/analytics/`, { headers: getHeaders() }).then(handleResponse),

  // Knowledge Graph
  getGraphStats: () =>
    fetch(`${BASE_URL}/knowledge-graph/stats`, { headers: getHeaders() }).then(handleResponse),

  getFullGraph: () =>
    fetch(`${BASE_URL}/knowledge-graph/full`, { headers: getHeaders() }).then(handleResponse),
};
