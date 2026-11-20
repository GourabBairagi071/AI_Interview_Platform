import requests
BASE_URL = 'http://127.0.0.1:8000/api/v1'
admin_login = requests.post(f'{BASE_URL}/auth/login', json={'email': 'admin@interviewplatform.ai', 'password': 'AdminPass123!'})
token = admin_login.json()["access_token"]
admin_headers = {'Authorization': f'Bearer {token}'}
q_payload = {
    'question': 'Explain CAP theorem tradeoffs in distributed systems',
    'topic': 'Distributed Systems',
    'difficulty': 'Hard',
    'role': 'Backend Architect',
    'question_type': 'Technical',
    'explanation': 'Consistency, Availability, Partition Tolerance',
    'hints': ['Consider network netsplit conditions'],
    'is_verified': True,
    'is_published': True,
    'is_featured': True
}
q_resp = requests.post(f'{BASE_URL}/admin/questions', json=q_payload, headers=admin_headers)
print('STATUS:', q_resp.status_code)
print('TEXT:', q_resp.text)
