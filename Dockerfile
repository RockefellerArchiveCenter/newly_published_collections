FROM public.ecr.aws/lambda/python:3.12

# Install Python requirements
COPY requirements.txt .
RUN  pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Add code
COPY create_message.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "create_message.main" ]
