def test_session_scoped_api_credentials_isolation(client, seed_data):
    # Visitor A logs in
    login_a = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "admin123"})
    assert login_a.status_code == 200
    token_a = login_a.json()["access_token"]
    
    # Visitor B logs in (SAME account)
    login_b = client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "admin123"})
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]
    
    # Visitor A sets their API key
    res = client.put(
        "/api/v1/settings/",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"gemini_api_key": "VISITOR_A_KEY", "llm_provider": "gemini"}
    )
    assert res.status_code == 200
    assert res.json()["gemini_api_key_set"] == True

    # Visitor B checks their settings, should NOT see Visitor A's key
    res = client.get(
        "/api/v1/settings/",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res.status_code == 200
    assert res.json()["gemini_api_key_set"] == False
    
    # Visitor B sets their own API key
    res = client.put(
        "/api/v1/settings/",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"openai_api_key": "VISITOR_B_KEY", "llm_provider": "openai"}
    )
    assert res.status_code == 200
    assert res.json()["openai_api_key_set"] == True
    
    # Check Visitor A again, they should not see B's key
    res = client.get(
        "/api/v1/settings/",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res.status_code == 200
    assert res.json()["gemini_api_key_set"] == True
    assert res.json()["openai_api_key_set"] == False

    # Visitor A logs out
    res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res.status_code == 200
    
    # Visitor A token is now invalid/expired session
    res = client.get(
        "/api/v1/settings/",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res.status_code == 401
    
    # Visitor B is STILL logged in
    res = client.get(
        "/api/v1/settings/",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res.status_code == 200
    assert res.json()["openai_api_key_set"] == True
