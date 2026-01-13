from django import forms
from django.core.exceptions import ValidationError

# Try multiple ways to import pandas
PANDAS_AVAILABLE = False
PANDAS_ERROR = None
pd = None
io = None

try:
    import pandas as pd
    import io
    PANDAS_AVAILABLE = True
    print(f"DEBUG: Successfully imported pandas {pd.__version__}")
except ImportError as e:
    PANDAS_ERROR = str(e)
    print(f"DEBUG: Failed to import pandas: {PANDAS_ERROR}")

    # Try alternative import methods
    try:
        import sys
        import subprocess
        # Try to install pandas if not available
        print("DEBUG: Attempting to install pandas...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
        import pandas as pd
        import io
        PANDAS_AVAILABLE = True
        print(f"DEBUG: Successfully installed and imported pandas {pd.__version__}")
    except Exception as install_error:
        PANDAS_ERROR = f"Original error: {PANDAS_ERROR}. Install error: {str(install_error)}"
        print(f"DEBUG: Failed to install pandas: {PANDAS_ERROR}")

# If pandas is still not available, provide a fallback
if not PANDAS_AVAILABLE:
    print("WARNING: pandas not available, customer import will not work")
    print(f"Error details: {PANDAS_ERROR}")
    print("To fix this, run: pip install pandas openpyxl")

class CustomerImportForm(forms.Form):
    """Form for importing customers from CSV/Excel files"""

    file = forms.FileField(
        label='Customer File',
        help_text='Upload CSV or Excel file with customer data. Required columns: full_name, phone_number. Optional: email, company_name',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        })
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            raise ValidationError('Please select a file to upload.')

        # Check file extension
        file_name = file.name.lower()
        if not (file_name.endswith('.csv') or file_name.endswith('.xlsx') or file_name.endswith('.xls')):
            raise ValidationError('Please upload a CSV or Excel file (.csv, .xlsx, .xls)')

        # Check file size (max 5MB)
        if file.size > 5 * 1024 * 1024:
            raise ValidationError('File size must be less than 5MB')

        return file

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get('file')

        if not file:
            return cleaned_data

        # Check if pandas is available
        if not PANDAS_AVAILABLE:
            error_msg = 'pandas library is required for file processing. '
            if PANDAS_ERROR:
                error_msg += f'Import error: {PANDAS_ERROR}. '
            error_msg += 'Please install it with: pip install pandas openpyxl'
            raise ValidationError(error_msg)

        return cleaned_data

    def process_file(self):
        """Process the uploaded file and return customer data"""
        file = self.cleaned_data.get('file')
        if not file:
            return [], []

        if not PANDAS_AVAILABLE:
            raise ValidationError('pandas library is required for file processing. Please install it with: pip install pandas openpyxl')

        try:
            # Read file based on extension
            file_name = file.name.lower()
            if file_name.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file.read()))
            else:
                df = pd.read_excel(io.BytesIO(file.read()))

            # Validate required columns
            required_columns = ['full_name', 'phone_number']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValidationError(f'Missing required columns: {", ".join(missing_columns)}')

            # Process data
            customers_data = []
            errors = []

            for index, row in df.iterrows():
                try:
                    # Required fields
                    full_name = str(row['full_name']).strip()
                    phone_number = str(row['phone_number']).strip()

                    if not full_name or full_name.lower() in ['nan', 'none', '']:
                        errors.append(f'Row {index + 2}: Missing full_name')
                        continue

                    if not phone_number or phone_number.lower() in ['nan', 'none', '']:
                        errors.append(f'Row {index + 2}: Missing phone_number')
                        continue

                    # Optional fields
                    email = str(row.get('email', '')).strip()
                    if email.lower() in ['nan', 'none']:
                        email = ''

                    company_name = str(row.get('company_name', '')).strip()
                    if company_name.lower() in ['nan', 'none']:
                        company_name = ''

                    customers_data.append({
                        'full_name': full_name,
                        'phone_number': phone_number,
                        'email': email,
                        'company_name': company_name,
                        'row_number': index + 2
                    })

                except Exception as e:
                    errors.append(f'Row {index + 2}: Error processing data - {str(e)}')

            return customers_data, errors

        except Exception as e:
            raise ValidationError(f'Error reading file: {str(e)}')
