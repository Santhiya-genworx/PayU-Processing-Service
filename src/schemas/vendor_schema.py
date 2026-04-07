"""module: vendor_schema.py"""

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class VendorBase(BaseModel):
    """Pydantic model representing the base structure of a vendor. This model includes fields for the vendor's name, email, address, country code, mobile number, GST number, bank name, account holder name, account number, and IFSC code. Each field has specific validation rules to ensure that the data provided for a vendor is accurate and conforms to expected formats. For example, the email field must be a valid email address, the country code must follow a specific pattern (e.g., "+1" for USA), the mobile number must contain only digits and be within a certain length range, the GST number must match the standard format for GST in India, and the IFSC code must match the standard format for Indian bank IFSC codes. This model serves as the basis for defining the structure of vendor data within the system, allowing for validation and consistent representation of vendor information when creating or processing purchase orders and invoices."""

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
    def validate_gst(cls, v: str) -> str:
        """Validates the GST number format. The GST number must follow the standard format for GST in India, which consists of 15 characters: the first 2 characters are digits representing the state code, followed by 5 uppercase letters representing the PAN, then 4 digits, 1 uppercase letter, the letter 'Z', and finally 1 alphanumeric character. If the provided GST number does not match this pattern, a ValueError is raised indicating an invalid format. If the validation passes, the GST number is returned in uppercase format."""
        gst_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}$"
        if not re.match(gst_pattern, v):
            raise ValueError("Invalid GST number format")
        return v.upper()

    # IFSC Validation
    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc(cls, v: str) -> str:
        """Validates the IFSC code format. The IFSC code must follow the standard format for Indian bank IFSC codes, which consists of 11 characters: the first 4 characters are uppercase letters representing the bank code, followed by the digit '0', and then 6 alphanumeric characters representing the branch code. If the provided IFSC code does not match this pattern, a ValueError is raised indicating an invalid format. If the validation passes, the IFSC code is returned in uppercase format."""
        ifsc_pattern = r"^[A-Z]{4}0[A-Z0-9]{6}$"
        if not re.match(ifsc_pattern, v):
            raise ValueError("Invalid IFSC code format")
        return v.upper()

    # Account Number Validation
    @field_validator("account_number")
    @classmethod
    def validate_account_number(cls, v: str) -> str:
        """Validates the account number format. The account number must contain only digits and be between 9 and 18 characters in length. If the provided account number does not match this pattern, a ValueError is raised indicating that the account number must contain only digits. If the validation passes, the account number is returned as is."""
        if not v.isdigit():
            raise ValueError("Account number must contain only digits")
        return v

    model_config = ConfigDict(from_attributes=True)
