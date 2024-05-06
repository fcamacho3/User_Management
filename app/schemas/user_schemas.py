from typing import ClassVar
from builtins import ValueError, any, bool, str
from urllib.parse import urlparse
from pydantic import BaseModel, EmailStr, Field, validator, root_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid
import re
from app.models.user_model import UserRole
from app.utils.nickname_gen import generate_nickname


def validate_url(url: Optional[str]) -> Optional[str]:
    if url is None:
        return url
    url_regex = r'^https?:\/\/[^\s/$.?#].[^\s]*$'
    if not re.match(url_regex, url):
        raise ValueError('Invalid URL format')
    return url

class UserBase(BaseModel):
    email: EmailStr = Field(..., example="john.doe@example.com", max_length=255)
    nickname: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r'^[\w-]+$', example=generate_nickname())
    first_name: Optional[str] = Field(None, max_length=100, example="John")
    last_name: Optional[str] = Field(None, max_length=100, example="Doe")
    bio: Optional[str] = Field(None, max_length=500, example="Experienced software developer specializing in web applications.")
    profile_picture_url: Optional[str] = Field(None, max_length=255, example="https://example.com/profiles/john.jpg")
    linkedin_profile_url: Optional[str] = Field(None, max_length=255, example="https://linkedin.com/in/johndoe")
    github_profile_url: Optional[str] = Field(None, max_length=255, example="https://github.com/johndoe")
    role: UserRole

    _validate_urls = validator('profile_picture_url', 'linkedin_profile_url', 'github_profile_url', pre=True, allow_reuse=True)(validate_url)
 
    @validator('email')
    def validate_email(cls, v):
        # Normalize the email to lowercase
        normalized_email = v.lower()
        # Check if the email ends with one of the allowed TLDs
        if not re.search(r"\.(com|org|edu|net|gov)$", normalized_email):
            raise ValueError("Email must end with one of the following domains: .com, .org, .edu, .net, .gov")
        return normalized_email

    class Config:
        from_attributes = True

class UserCreate(UserBase):
    password: str = Field(..., example="Secure*1234")

    # Define min_length and max_length as class variables that are not model fields
    min_length: ClassVar[int] = 8
    max_length: ClassVar[int] = 50

    @validator('password')
    def password_validation(cls, value):
        if len(value) < cls.min_length or len(value) > cls.max_length:
            raise ValueError(f'Password must be between {cls.min_length} and {cls.max_length} characters')
        if not re.search("[A-Z]", value):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search("[a-z]", value):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r"\d", value):
            raise ValueError('Password must contain at least one digit')
        if not re.search("[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError('Password must contain at least one special character')
        if " " in value:
            raise ValueError('Password must not contain spaces')
        return value

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(None, example="john.doe@example.com")
    nickname: Optional[str] = Field(None, min_length=3, pattern=r'^[\w-]+$', example="john_doe123")
    first_name: Optional[str] = Field(None, example="John")
    last_name: Optional[str] = Field(None, example="Doe")
    bio: Optional[str] = Field(None, example="Experienced software developer specializing in web applications.")
    profile_picture_url: Optional[str] = Field(None, example="https://example.com/profiles/john.jpg")
    linkedin_profile_url: Optional[str] =Field(None, example="https://linkedin.com/in/johndoe")
    github_profile_url: Optional[str] = Field(None, example="https://github.com/johndoe")
    role: Optional[str] = Field(None, example="AUTHENTICATED")

    @root_validator(pre=True)
    def check_at_least_one_value(cls, values):
        if not any(values.values()):
            raise ValueError("At least one field must be provided for update")
        return values

class UserResponse(UserBase):
    id: uuid.UUID = Field(..., example=uuid.uuid4())
    email: EmailStr = Field(..., example="john.doe@example.com")
    nickname: Optional[str] = Field(None, min_length=3, pattern=r'^[\w-]+$', example=generate_nickname())    
    is_professional: Optional[bool] = Field(default=False, example=True)
    role: UserRole

class LoginRequest(BaseModel):
    email: str = Field(..., example="john.doe@example.com")
    password: str = Field(..., example="Secure*1234")

class ErrorResponse(BaseModel):
    error: str = Field(..., example="Not Found")
    details: Optional[str] = Field(None, example="The requested resource was not found.")

class UserListResponse(BaseModel):
    items: List[UserResponse] = Field(..., example=[{
        "id": uuid.uuid4(), "nickname": generate_nickname(), "email": "john.doe@example.com",
        "first_name": "John", "bio": "Experienced developer", "role": "AUTHENTICATED",
        "last_name": "Doe", "bio": "Experienced developer", "role": "AUTHENTICATED",
        "profile_picture_url": "https://example.com/profiles/john.jpg", 
        "linkedin_profile_url": "https://linkedin.com/in/johndoe", 
        "github_profile_url": "https://github.com/johndoe"
    }])
    total: int = Field(..., example=100)
    page: int = Field(..., example=1)
    size: int = Field(..., example=10)

# New Feature: class for updating user profile
class UserUpdateProfile(BaseModel):
    nickname: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r'^[\w-]+$', example=generate_nickname())
    first_name: Optional[str] = Field(None, max_length=100, example="John")
    last_name: Optional[str] = Field(None, max_length=100, example="Doe")
    bio: Optional[str] = Field(None, max_length=500, example="Experienced software developer specializing in web applications.")
    profile_picture_url: Optional[str] = Field(None, max_length=255, example="https://example.com/profiles/john.jpg")
    linkedin_profile_url: Optional[str] = Field(None, max_length=255, example="https://linkedin.com/in/johndoe")
    github_profile_url: Optional[str] = Field(None, max_length=255, example="https://github.com/johndoe")

    @root_validator(pre=True)
    def check_at_least_one_value(cls, values):
        if not any(values.values()):
            raise ValueError("At least one field must be provided for update")
        return values

    @validator('nickname', pre=True, always=True)
    def validate_nickname(cls, v):
        if v is not None:
            reserved_keywords = {"admin", "moderator", "null", "manager", "anonymous", "authenticated"}
            if v.lower() in reserved_keywords:
                raise ValueError("This nickname is reserved and cannot be used.")
        return v

    @validator('first_name')
    def validate_first_name(cls, v):
        if v and not re.match(r"^[a-zA-Z\s'-]+$", v):
            raise ValueError("First name can only contain letters, spaces, hyphens, or apostrophes.")
        return v

    @validator('last_name')
    def validate_last_name(cls, v):
        if v and not re.match(r"^[a-zA-Z\s'-]+$", v):
            raise ValueError("Last name can only contain letters, spaces, hyphens, or apostrophes.")
        return v

    @validator('profile_picture_url', pre=True, always=True)
    def validate_profile_picture_url(cls, v):
        if v is None:
            return v  # If the URL is optional, allow None values
        parsed_url = urlparse(v)
        if not re.search(r"\.(jpg|jpeg|png)$", parsed_url.path):
            raise ValueError("Profile picture URL must point to a valid image file (JPEG, PNG).")
        if parsed_url.scheme not in ['http', 'https']:
            raise ValueError("Profile picture URL must use http or https.")
        return v

    @validator('linkedin_profile_url', pre=True, always=True)
    def validate_linkedin_profile_url(cls, v):
        if v is None:
            return v
        parsed_url = urlparse(v)
        if parsed_url.scheme not in ['http', 'https']:
            raise ValueError("LinkedIn profile URL must use http or https.")
        if parsed_url.netloc != "linkedin.com" or not parsed_url.path.startswith("/in/"):
            raise ValueError("Invalid LinkedIn profile URL format.")
        return v

    @validator('github_profile_url', pre=True, always=True)
    def validate_github_profile_url(cls, v):
        if v is None:
            return v
        parsed_url = urlparse(v)
        if parsed_url.scheme not in ['http', 'https']:
            raise ValueError("GitHub profile URL must use http or https.")
        if parsed_url.netloc != "github.com":
            raise ValueError("Invalid GitHub profile URL format.")
        return v