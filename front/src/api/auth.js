export async function refreshToken() {
  const refresh = localStorage.getItem('refresh');

  if (!refresh) {
    throw new Error('Refresh 토큰 없음');
  }

  const response = await fetch(`${API_BASE}/accounts/token/refresh/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh }),
  });

  if (!response.ok) {
    throw new Error('토큰 갱신 실패');
  }

  const data = await response.json();
  localStorage.setItem('access', data.access);

  return data.access;
}