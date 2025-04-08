# Use the official Python image from Docker Hub
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Set environment variables (if necessary)
ENV MONGO_URI="mongodb://127.0.0.1:27017"
ENV DB_NAME="KUBRC_DB"
ENV COLLECTION_NAME="payments"
ENV XLSX_GDRIVE_ID="1HKkJSE_zauenx7PB285Q8t44KvOwvwiwy4zeAJv_f3E"
ENV XLSX_FILE="KUBRC_PaymentDetails.xlsx"

# Expose any required ports (if needed for your application)
EXPOSE 5000

# Run the Python script
CMD ["python", "main.py"]
