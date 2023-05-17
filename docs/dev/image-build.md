
#Pre-requisites
##Make sure necessary  docker files and docker compose files are present at the root of repo 

#Approach 1: 

#Build and tag  Docker Image Using Dockerfile
##Note: while running below commands user has to be at root of the repo "/repo-location/arcas"


## Step1: The below command will build the arcas-cli using Dockerfile from the same directory.

      docker build -t arcas-cli:latest -f Dockerfile.be .

    1. -t is for tagging the image.
    2. arcas-cli is the name of the image .
    3. latest is  the tag name. If you don’t add any tag, it defaults to the tag named latest.
    4. -f Dockerfile.be . means, we are referring to the Dockerfile.be location as the docker build context.



        
## Step2: The below command will build the sivt-ui using Dockerfile from the same directory.

      docker build -t sivt-ui:latest -f Dockerfile.web .

    1. -t is for tagging the image.
    2. sivt-ui is the name of the image .
    3. latest is the tag name. If you don’t add any tag, it defaults to the tag named latest.
    4. -f Dockerfile.web . means, we are referring to the Dockerfile.web location as the docker build context.



##Now after building the image we will run the Docker image. The command will be

##step1: Run arcas-cli image

    docker run --rm --network=host -v /var/run/docker.sock:/var/run/docker.sock -d -p 5000:5000 arcas-cli:latest
    
    Here,
        -p :flag for the port number, the format is local-port:container-port
        --rm: This option automatically removes the container when it exits. This helps avoid accumulating stopped containers over time.
        --network=host: This option sets the container's network mode to "host", which means that it shares the same network stack as the host machine. This allows the container to access the host's network interfaces directly, without requiring any port mapping.
        -v /var/run/docker.sock:/var/run/docker.sock: This option mounts the Docker socket from the host machine into the container, allowing the container to interact with the Docker daemon running on the host machine.
        -d: This option runs the container in detached mode, meaning it runs in the background and doesn't keep the terminal open.
##step2: Run sivt-ui image
    docker run -it -p 8888:8888  sivt-ui:latest
    
    Here,
        -p flag for the port number, the format is local-port:container-port
        -it flag for the running the container in interactive mode

#Output : Once we performed above steps application will be up and running at localhost:8888

#Approach 2:

#Using docker compose for build and run the image
##Note: while running below commands user has to be at root of the repo "/repo-location/arcas"

##Step1:Build  and run image 
    export ARCAS_CLI_IMAGE_TAG=custom-cli-tag
    export SIVT_UI_IMAGE_TAG=custom-ui-tag
    docker-compose up


#Output : Once we performed above steps application will be up and running at localhost:8888

#Debugging containers or Arcas Usage.
    docker ps 
    Above command list down the running containers with container id
    
    docker exec -it container_id /bin/bash
    In order to execute commands on running containers, you have to execute “docker exec” and specify the container name (or ID) as well as the command to be executed on this container.
    After executing the above command aracs related commands( mentioned below ) can be executed inside the container 
    
    arcas --help


