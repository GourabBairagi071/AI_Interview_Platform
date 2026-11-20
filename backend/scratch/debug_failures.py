import requests
BASE_URL = 'http://127.0.0.1:8000/api/v1'
admin_login = requests.post(f'{BASE_URL}/auth/login', json={'email': 'admin@interviewplatform.ai', 'password': 'AdminPass123!'})
token = admin_login.json()["access_token"]
admin_headers = {'Authorization': f'Bearer {token}'}

# 3: kpis
dash = requests.get(f'{BASE_URL}/admin/dashboard?time_range=30d', headers=admin_headers)
kpis = dash.json().get('kpis', {})
print('DASH KPIS:', kpis)

# 4: candidate management
users = requests.get(f'{BASE_URL}/admin/users?role=CANDIDATE', headers=admin_headers)
print('USERS STATUS:', users.status_code, 'JSON:', users.json())

# 7: practice questions
q_post = requests.post(f'{BASE_URL}/admin/questions', json={
    'technology': 'Python', 'topic': 'Algorithms', 'question': 'Binary search?', 'difficulty': 'Easy', 'question_type': 'Technical', 'explanation': 'O(log n)'
}, headers=admin_headers)
print('Q POST STATUS:', q_post.status_code, 'TEXT:', q_post.text)

# 8: coding problems
cp = requests.get(f'{BASE_URL}/admin/coding/problems?page_size=1', headers=admin_headers)
print('CP STATUS:', cp.status_code, 'JSON:', cp.json() if cp.status_code==200 else cp.text)

# 15: rag management
rag = requests.get(f'{BASE_URL}/admin/rag/status', headers=admin_headers)
print('RAG STATUS:', rag.status_code, 'JSON:', rag.json())

# 29: audit logs
audit = requests.get(f'{BASE_URL}/admin/audit-logs', headers=admin_headers)
print('AUDIT STATUS:', audit.status_code, 'JSON:', audit.json() if audit.status_code==200 else audit.text)
