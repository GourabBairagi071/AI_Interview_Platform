import asyncio
import sys
import uuid
import httpx

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, ".")

BASE_URL = "http://127.0.0.1:8000/api/v1"

async def run_tests():
    print("=== STARTING TASK PHASE 7 ANTI-CHEATING BACKEND TEST ===")
    
    # We will test using direct FastAPI test client or HTTP if server is running.
    # Let's import the app and use httpx.AsyncClient with ASGITransport for hermetic, fast testing!
    from app.main import app
    from httpx import ASGITransport

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create User 1 & 2
        email_1 = f"anticheat_u1_{uuid.uuid4().hex[:6]}@example.com"
        email_2 = f"anticheat_u2_{uuid.uuid4().hex[:6]}@example.com"
        pwd = "Password123!"

        resp1 = await client.post("/api/v1/auth/register", json={"email": email_1, "password": pwd, "full_name": "Proctored Candidate 1"})
        assert resp1.status_code == 201, f"User 1 reg failed: {resp1.text}"
        login1 = await client.post("/api/v1/auth/login", json={"email": email_1, "password": pwd})
        token1 = login1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        resp2 = await client.post("/api/v1/auth/register", json={"email": email_2, "password": pwd, "full_name": "Proctored Candidate 2"})
        assert resp2.status_code == 201, f"User 2 reg failed: {resp2.text}"
        login2 = await client.post("/api/v1/auth/login", json={"email": email_2, "password": pwd})
        token2 = login2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        print("✓ Created Users 1 & 2")

        # 2. Create Interview for User 1
        interview_resp = await client.post(
            "/api/v1/interview",
            headers=headers1,
            json={
                "job_role": "Python Backend Engineer",
                "difficulty": "Intermediate",
                "experience_level": "Mid-Level",
                "interview_type": "Technical",
                "number_of_questions": 3,
            }
        )
        assert interview_resp.status_code == 201, f"Interview creation failed: {interview_resp.text}"
        interview_id = interview_resp.json()["interview"]["id"]
        print(f"✓ Created Interview: {interview_id}")

        # 3. Test Unauthorized Access (No Token)
        unauth_resp = await client.get(f"/api/v1/interview/{interview_id}/anti-cheating/events")
        assert unauth_resp.status_code == 401 or unauth_resp.status_code == 403, f"Expected 401/403, got {unauth_resp.status_code}"
        print("✓ Test passed: Unauthorized request rejected with 401/403")

        # 4. Test Cross-User Access (User 2 accessing User 1's interview)
        cross_resp = await client.get(f"/api/v1/interview/{interview_id}/anti-cheating/events", headers=headers2)
        assert cross_resp.status_code == 403, f"Expected 403, got {cross_resp.status_code}"
        print("✓ Test passed: Cross-user access rejected with 403 Forbidden")

        # 5. Test Non-Existent Interview ID
        fake_id = str(uuid.uuid4())
        notfound_resp = await client.get(f"/api/v1/interview/{fake_id}/anti-cheating/events", headers=headers1)
        assert notfound_resp.status_code == 404, f"Expected 404, got {notfound_resp.status_code}"
        print("✓ Test passed: Non-existent interview returned 404 Not Found")

        # 6. Test Initial Empty Events & Summary
        empty_events = await client.get(f"/api/v1/interview/{interview_id}/anti-cheating/events", headers=headers1)
        assert empty_events.status_code == 200
        assert empty_events.json()["total"] == 0
        assert empty_events.json()["events"] == []

        init_summary = await client.get(f"/api/v1/interview/{interview_id}/anti-cheating/summary", headers=headers1)
        assert init_summary.status_code == 200
        summary_data = init_summary.json()
        assert summary_data["overall_status"] == "CLEAR"
        assert summary_data["total_events"] == 0
        assert summary_data["risk_score"] == 0.0
        print("✓ Test passed: Initial empty events and CLEAR summary")

        # 7. Test Recording Invalid Event Data (validation error)
        bad_req = await client.post(
            f"/api/v1/interview/{interview_id}/anti-cheating/events",
            headers=headers1,
            json={
                "event_type": "INVALID_TYPE",
                "confidence": 1.5,
                "description": "",
            }
        )
        assert bad_req.status_code == 422, f"Expected 422 Unprocessable Entity, got {bad_req.status_code}"
        print("✓ Test passed: Invalid event data rejected with 422")

        # 8. Record Real Events
        # Event A: FACE_MISSING (Medium severity, 4.5 seconds duration, 0.9 confidence)
        evt_a = await client.post(
            f"/api/v1/interview/{interview_id}/anti-cheating/events",
            headers=headers1,
            json={
                "event_type": "FACE_MISSING",
                "severity": "MEDIUM",
                "duration": 4.5,
                "confidence": 0.9,
                "description": "Candidate face not detected for 4.5 seconds",
                "metadata": {"consecutive_frames": 9, "camera_active": True},
            }
        )
        assert evt_a.status_code == 201, f"Record event A failed: {evt_a.text}"
        evt_a_data = evt_a.json()
        assert evt_a_data["event_type"] == "FACE_MISSING"
        assert evt_a_data["duration"] == 4.5
        assert evt_a_data["metadata"]["consecutive_frames"] == 9
        print("✓ Test passed: Recorded FACE_MISSING event")

        # Event B: MULTIPLE_PERSON (High severity, 3.2 seconds duration, 0.95 confidence)
        evt_b = await client.post(
            f"/api/v1/interview/{interview_id}/anti-cheating/events",
            headers=headers1,
            json={
                "event_type": "MULTIPLE_PERSON",
                "severity": "HIGH",
                "duration": 3.2,
                "confidence": 0.95,
                "description": "Multiple faces (2) detected in frame",
                "metadata": {"detected_faces": 2},
            }
        )
        assert evt_b.status_code == 201, f"Record event B failed: {evt_b.text}"
        print("✓ Test passed: Recorded MULTIPLE_PERSON event")

        # 9. Test Candidate Face Registration Endpoint
        sample_encoding = [0.12, 0.45, 0.88, 0.33, 0.55, 0.22, 0.91, 0.64] * 8  # 64-dim vector
        reg_resp = await client.post(
            f"/api/v1/interview/{interview_id}/anti-cheating/register-face",
            headers=headers1,
            json={
                "encoding": sample_encoding,
                "metadata": {"source": "webcam", "width": 480, "height": 360},
            }
        )
        assert reg_resp.status_code == 200, f"Register face failed: {reg_resp.text}"
        reg_data = reg_resp.json()
        assert reg_data["registered"] is True
        assert reg_data["vector_dimension"] == 64
        print("✓ Test passed: Candidate face registered successfully (64-dim vector)")

        # Test cross-user attempt to register face -> 403 Forbidden
        reg_cross = await client.post(
            f"/api/v1/interview/{interview_id}/anti-cheating/register-face",
            headers=headers2,
            json={"encoding": sample_encoding}
        )
        assert reg_cross.status_code == 403, f"Expected 403, got {reg_cross.status_code}"
        print("✓ Test passed: Cross-user face registration rejected with 403")

        # 10. Record Event C: IDENTITY_MISMATCH
        evt_c = await client.post(
            f"/api/v1/interview/{interview_id}/anti-cheating/events",
            headers=headers1,
            json={
                "event_type": "IDENTITY_MISMATCH",
                "severity": "HIGH",
                "duration": 3.0,
                "confidence": 0.88,
                "description": "Candidate identity does not match baseline (similarity: 42%)",
                "metadata": {"similarityScore": 0.42, "threshold": 0.62},
            }
        )
        assert evt_c.status_code == 201, f"Record event C failed: {evt_c.text}"
        print("✓ Test passed: Recorded IDENTITY_MISMATCH event")

        # 11. Record Event D: MOBILE_DETECTED
        evt_d = await client.post(
            f"/api/v1/interview/{interview_id}/anti-cheating/events",
            headers=headers1,
            json={
                "event_type": "MOBILE_DETECTED",
                "severity": "HIGH",
                "duration": 2.5,
                "confidence": 0.92,
                "description": "Mobile phone detected in frame for 2.5s",
                "metadata": {"deviceClass": "cell phone"},
            }
        )
        assert evt_d.status_code == 201, f"Record event D failed: {evt_d.text}"
        print("✓ Test passed: Recorded MOBILE_DETECTED event")

        # 12. Record Event E: DEVICE_DETECTED
        evt_e = await client.post(
            f"/api/v1/interview/{interview_id}/anti-cheating/events",
            headers=headers1,
            json={
                "event_type": "DEVICE_DETECTED",
                "severity": "MEDIUM",
                "duration": 4.0,
                "confidence": 0.85,
                "description": "Unauthorized secondary electronic device visible for 4.0s",
                "metadata": {"deviceClass": "laptop"},
            }
        )
        assert evt_e.status_code == 201, f"Record event E failed: {evt_e.text}"
        print("✓ Test passed: Recorded DEVICE_DETECTED event")

        # 13. List Events - Verify all 5 events
        events_resp = await client.get(f"/api/v1/interview/{interview_id}/anti-cheating/events", headers=headers1)
        assert events_resp.status_code == 200
        events_list = events_resp.json()
        assert events_list["total"] == 5
        assert len(events_list["events"]) == 5
        types_recorded = [e["event_type"] for e in events_list["events"]]
        assert "FACE_MISSING" in types_recorded
        assert "MULTIPLE_PERSON" in types_recorded
        assert "IDENTITY_MISMATCH" in types_recorded
        assert "MOBILE_DETECTED" in types_recorded
        assert "DEVICE_DETECTED" in types_recorded
        print("✓ Test passed: Retrieved event list with all 5 security event types")

        # 14. Comprehensive Summary Verification
        summary_resp = await client.get(f"/api/v1/interview/{interview_id}/anti-cheating/summary", headers=headers1)
        assert summary_resp.status_code == 200
        sum_data = summary_resp.json()
        assert sum_data["total_events"] == 5
        assert sum_data["face_missing_events"] == 1
        assert sum_data["multiple_person_events"] == 1
        assert sum_data["identity_mismatch_events"] == 1
        assert sum_data["device_events"] == 2  # MOBILE_DETECTED + DEVICE_DETECTED
        assert sum_data["total_suspicious_duration"] == 17.2  # 4.5 + 3.2 + 3.0 + 2.5 + 4.0
        assert sum_data["overall_status"] == "SUSPICIOUS"
        assert sum_data["risk_score"] > 60.0
        print(f"✓ Test passed: Comprehensive summary verified: status={sum_data['overall_status']}, risk_score={sum_data['risk_score']}")

    print("\nALL ANTI-CHEATING BACKEND & REMAINING FEATURE TESTS PASSED SUCCESSFULLY! ✓")

if __name__ == "__main__":
    asyncio.run(run_tests())

