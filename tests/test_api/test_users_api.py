from builtins import str
from unittest.mock import AsyncMock, patch
import pytest
from app.services.user_service import UserService
from httpx import AsyncClient
from app.main import app
from app.models.user_model import User, UserRole
from app.utils.nickname_gen import generate_nickname
from app.utils.security import hash_password
from app.services.jwt_service import decode_token  # Import your FastAPI app

# Example of a test function using the async_client fixture
@pytest.mark.asyncio
async def test_create_user_access_denied(async_client, user_token, email_service):
    headers = {"Authorization": f"Bearer {user_token}"}
    # Define user data for the test
    user_data = {
        "nickname": generate_nickname(),
        "email": "test@example.com",
        "password": "sS#fdasrongPassword123!",
    }
    # Send a POST request to create a user
    response = await async_client.post("/users/", json=user_data, headers=headers)
    # Asserts
    assert response.status_code == 403

# You can similarly refactor other test functions to use the async_client fixture
@pytest.mark.asyncio
async def test_retrieve_user_access_denied(async_client, verified_user, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await async_client.get(f"/users/{verified_user.id}", headers=headers)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_retrieve_user_access_allowed(async_client, admin_user, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.get(f"/users/{admin_user.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(admin_user.id)

@pytest.mark.asyncio
async def test_update_user_email_access_denied(async_client, verified_user, user_token):
    updated_data = {"email": f"updated_{verified_user.id}@example.com"}
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await async_client.put(f"/users/{verified_user.id}", json=updated_data, headers=headers)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_update_user_email_access_allowed(async_client, admin_user, admin_token):
    updated_data = {"email": f"updated_{admin_user.id}@example.com"}
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.put(f"/users/{admin_user.id}", json=updated_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == updated_data["email"]


@pytest.mark.asyncio
async def test_delete_user(async_client, admin_user, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    delete_response = await async_client.delete(f"/users/{admin_user.id}", headers=headers)
    assert delete_response.status_code == 204
    # Verify the user is deleted
    fetch_response = await async_client.get(f"/users/{admin_user.id}", headers=headers)
    assert fetch_response.status_code == 404

@pytest.mark.asyncio
async def test_create_user_duplicate_email(async_client, verified_user):
    user_data = {
        "email": verified_user.email,
        "password": "AnotherPassword123!",
        "role": UserRole.ADMIN.name
    }
    response = await async_client.post("/register/", json=user_data)
    assert response.status_code == 400
    assert "Email already exists" in response.json().get("detail", "")

@pytest.mark.asyncio
async def test_create_user_invalid_email(async_client):
    user_data = {
        "email": "notanemail",
        "password": "ValidPassword123!",
    }
    response = await async_client.post("/register/", json=user_data)
    assert response.status_code == 422

import pytest
from app.services.jwt_service import decode_token
from urllib.parse import urlencode

@pytest.mark.asyncio
async def test_login_success(async_client, verified_user):
    # Attempt to login with the test user
    form_data = {
        "username": verified_user.email,
        "password": "MySuperPassword$1234"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    
    # Check for successful login response
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Use the decode_token method from jwt_service to decode the JWT
    decoded_token = decode_token(data["access_token"])
    assert decoded_token is not None, "Failed to decode token"
    assert decoded_token["role"] == "AUTHENTICATED", "The user role should be AUTHENTICATED"

@pytest.mark.asyncio
async def test_login_user_not_found(async_client):
    form_data = {
        "username": "nonexistentuser@here.edu",
        "password": "DoesNotMatter123!"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response.status_code == 401
    assert "Incorrect email or password." in response.json().get("detail", "")

@pytest.mark.asyncio
async def test_login_incorrect_password(async_client, verified_user):
    form_data = {
        "username": verified_user.email,
        "password": "IncorrectPassword123!"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response.status_code == 401
    assert "Incorrect email or password." in response.json().get("detail", "")

@pytest.mark.asyncio
async def test_login_unverified_user(async_client, unverified_user):
    form_data = {
        "username": unverified_user.email,
        "password": "MySuperPassword$1234"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_login_locked_user(async_client, locked_user):
    form_data = {
        "username": locked_user.email,
        "password": "MySuperPassword$1234"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response.status_code == 400
    assert "Account locked due to too many failed login attempts." in response.json().get("detail", "")
@pytest.mark.asyncio
async def test_delete_user_does_not_exist(async_client, admin_token):
    non_existent_user_id = "00000000-0000-0000-0000-000000000000"  # Valid UUID format
    headers = {"Authorization": f"Bearer {admin_token}"}
    delete_response = await async_client.delete(f"/users/{non_existent_user_id}", headers=headers)
    assert delete_response.status_code == 404

@pytest.mark.asyncio
async def test_update_user_github(async_client, admin_user, admin_token):
    updated_data = {"github_profile_url": "http://www.github.com/kaw393939"}
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.put(f"/users/{admin_user.id}", json=updated_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["github_profile_url"] == updated_data["github_profile_url"]

@pytest.mark.asyncio
async def test_update_user_linkedin(async_client, admin_user, admin_token):
    updated_data = {"linkedin_profile_url": "http://www.linkedin.com/kaw393939"}
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.put(f"/users/{admin_user.id}", json=updated_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["linkedin_profile_url"] == updated_data["linkedin_profile_url"]

@pytest.mark.asyncio
async def test_list_users_as_admin(async_client, admin_token):
    response = await async_client.get(
        "/users/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert 'items' in response.json()

@pytest.mark.asyncio
async def test_list_users_as_manager(async_client, manager_token):
    response = await async_client.get(
        "/users/",
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_list_users_unauthorized(async_client, user_token):
    response = await async_client.get(
        "/users/",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403  # Forbidden, as expected for regular user

# Tests for list_users skip & limit parameters
@pytest.mark.asyncio
async def test_list_users_invalid_skip_parameter(async_client: AsyncClient, admin_token: str):
    response = await async_client.get(
        "/users/?skip=-1",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "Parameters 'skip' and 'limit' must be non-negative integers" in response.json()["detail"]

@pytest.mark.asyncio
async def test_list_users_invalid_limit_parameter(async_client: AsyncClient, admin_token: str):
    response = await async_client.get(
        "/users/?limit=0",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "Parameters 'skip' and 'limit' must be non-negative integers" in response.json()["detail"]

@pytest.fixture
async def total_users(db_session):
    # Replace with the actual way to count users in your database
    count = await UserService.count(db_session)
    return count

@pytest.mark.asyncio
async def test_list_users_valid_parameters(async_client: AsyncClient, admin_token: str):
    response = await async_client.get(
        "/users/?skip=0&limit=10",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    json_response = response.json()
    assert 'items' in json_response
    assert json_response["total"] >= len(json_response["items"])  # Assuming you have users in your test database

# Test create_user while mocking email
@pytest.mark.asyncio
async def test_create_user_with_urls(async_client: AsyncClient, admin_token: str):
    user_data = {
        "email": "new.user@example.com",
        "nickname": "new_user",
        "first_name": "New",
        "last_name": "User",
        "bio": "New user bio",
        "profile_picture_url": "https://example.com/profiles/newuser.jpg",
        "linkedin_profile_url": "https://linkedin.com/in/newuser",
        "github_profile_url": "https://github.com/newuser",
        "role": "ANONYMOUS",
        "password": "Secure*1234"
    }
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Mock the email service
    with patch('app.services.email_service.EmailService.send_verification_email', new_callable=AsyncMock) as mock_send_email:
        response = await async_client.post("/users/", json=user_data, headers=headers)
    
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["email"] == "new.user@example.com"
        assert response_data["nickname"] == "new_user"
        assert response_data["first_name"] == "New"
        assert response_data["last_name"] == "User"
        assert response_data["bio"] == "New user bio"
        assert response_data["linkedin_profile_url"] == "https://linkedin.com/in/newuser"
        assert response_data["github_profile_url"] == "https://github.com/newuser"
        assert mock_send_email.called  # Ensures that the email service was called

# Tests for update_profile
@pytest.mark.asyncio
async def test_update_profile_success(async_client, verified_user_and_token):
    user, token = verified_user_and_token
    headers = {"Authorization": f"Bearer {token}"}
    updated_user_data = {
        "first_name": "TestUpdate",
        "last_name": "Profile",
        "bio": "Testing successful user profile update",
        "profile_picture_url": "https://www.example.com/updateduser.jpg",
        "linkedin_profile_url": "https://linkedin.com/in/updateduser",
        "github_profile_url": "https://github.com/updateduser"
    }
    response = await async_client.put("/update-profile/", json=updated_user_data, headers=headers)  
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["first_name"] == updated_user_data["first_name"]
    assert response_data["last_name"] == updated_user_data["last_name"]
    assert response_data["bio"] == updated_user_data["bio"]
    assert response_data["profile_picture_url"] == updated_user_data["profile_picture_url"]
    assert response_data["linkedin_profile_url"] == updated_user_data["linkedin_profile_url"]
    assert response_data["github_profile_url"] == updated_user_data["github_profile_url"]

@pytest.mark.asyncio
async def test_update_profile_unauthorized(async_client: AsyncClient):
    # Prepare headers without a valid token
    headers = {"Authorization": "Bearer invalid_or_missing_token"}

    # Attempt to update the profile with an invalid or missing token
    response = await async_client.put("/update-profile/", json={"nickname": "newNick"}, headers=headers)

    # Check the response for the expected 401 Unauthorized status
    assert response.status_code == 401
    assert "detail" in response.json()
    assert response.json()["detail"] == "Could not validate credentials"

@pytest.mark.asyncio
async def test_update_user_profile_duplicate_nickname(async_client, db_session, verified_user_and_token):
    first_user, token = verified_user_and_token
    test_user_1 = {
            "nickname": "TestUser",
            "first_name": "Test",
            "last_name": "User",
            "email": "testuser@example.com",
            "hashed_password": hash_password("Secure*1234!"),
            "role": UserRole.AUTHENTICATED,
            "email_verified": True,
            "is_locked": False,
        }
    first_test_user = User(**test_user_1)
    db_session.add(first_test_user)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {token}"}
    updated_user_data = {
        "nickname": "TestUser",
    }
    response = await async_client.put("/update-profile/", json=updated_user_data, headers=headers)  
    assert response.status_code == 400
    assert response.json()["detail"] == "Nickname already exists"

# Tests for update_professional_status route endpoint
@pytest.mark.asyncio
async def test_update_professional_status_as_admin(async_client: AsyncClient, admin_user, admin_token):
    """
    Test updating professional status and ensure email service is called, without actually sending an email.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    is_professional_status = True  # or False depending on the test case

    with patch('app.services.email_service.EmailService.send_professional_status_email_update', new_callable=AsyncMock) as mock_send_email:
        response = await async_client.put(f"/users/{admin_user.id}/set-professional/{is_professional_status}", headers=headers)

    assert response.status_code == 200
    assert response.json()['is_professional'] == is_professional_status
    mock_send_email.assert_awaited_once()  # Ensures that the email service was called

@pytest.mark.asyncio
async def test_update_professional_status_email_service_failure(async_client, admin_user, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    is_professional_status = True

    with patch('app.services.email_service.EmailService.send_professional_status_email_update', side_effect=Exception("Email failure"), new_callable=AsyncMock) as mock_send_email:
        response = await async_client.put(f"/users/{admin_user.id}/set-professional/{is_professional_status}", headers=headers)

    assert response.status_code == 200  # Ensure update still succeeds
    assert response.json()['is_professional'] == is_professional_status
    mock_send_email.assert_awaited_once()  # Ensure the email attempt was made
