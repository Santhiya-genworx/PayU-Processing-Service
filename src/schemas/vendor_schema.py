from pydantic import BaseModel, EmailStr, Field, field_validator
import re

class VendorBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    address: str = Field(..., min_length=5, max_length=500)
    country_code: str = Field(..., pattern=r"^\+\d{1,3}$")  
    mobile_number: str = Field(..., pattern=r"^\d{10,15}$")
    gst_number: str = Field(..., min_length=15, max_length=15)
    bank_name: str = Field(..., min_length=2, max_length=255)
    account_holder_name: str = Field(..., min_length=2, max_length=255)
    account_number: str = Field(..., min_length=9, max_length=18)
    ifsc_code: str = Field(..., min_length=11, max_length=11)

    # GST Validation
    @field_validator("gst_number")
    @classmethod
    def validate_gst(cls, v):
        gst_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}$"
        if not re.match(gst_pattern, v):
            raise ValueError("Invalid GST number format")
        return v.upper()

    # IFSC Validation
    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc(cls, v):
        ifsc_pattern = r"^[A-Z]{4}0[A-Z0-9]{6}$"
        if not re.match(ifsc_pattern, v):
            raise ValueError("Invalid IFSC code format")
        return v.upper()

    # Account Number Check
    @field_validator("account_number")
    @classmethod
    def validate_account_number(cls, v):
        if not v.isdigit():
            raise ValueError("Account number must contain only digits")
        return v