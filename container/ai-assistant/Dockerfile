# Use an official Python runtime as a parent image
# To do: optimize image
# To GET Tags https://catalog.redhat.com/software/containers/ubi8/python-39/6065b24eb92fbda3a4c65d8f?architecture=amd64&image=66187f6c0f4162fda50cb4ca
FROM openshift.artifactory.mycloud.intranatixis.com/ubi8/python-39:1-176

# Set system user
# To DO: use standard user
# USER 1

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY ./app /app


#Upgrade pip
RUN python -m pip install --upgrade pip

# Install Dependencies
RUN python -m pip install -r requirements.txt

# Run the FastAPI web service using uvicorn
CMD ["chainlit", "run","main.py","-h"]