# Trigger Tekton Pipelines for Tanzu Kubernetes Grid through Git Commits

Tekton pipelines support triggering of pipelines based on git commit changes. 

1. Complete the preparatory stages in **Prepare to Run Tekton Pipelines for Tanzu Kubernetes Grid**. 

2. Install the polling operator.

   ```sh
   kubectl apply -f https://github.com/bigkevmcd/tekton-polling-operator/releases/download/v0.4.0/release-v0.4.0.yaml
   ```

3. Browse to the `trigger-based` directory on Linux or SIVT VM directory to open the `trigger-bringup-res.yml` file.

4. Update the following fields. 
      
      - url: UPDATE FULL GIT PATH OF REPOSITORY
      - ref: BRANCH_NAME
      - frequency: 2m [time interval to check git changes. 2 minutes is set as default]
      - type: gitlab/github
 
   Save changes and exit. 

5. Open `trigger-bringup-pipeline.yml`.

6. Update the following fields.

    - default: "UPDATE IMAGE LOCATION" to docker.io/library/service_installer_tekton:v153
    - default: "UPDATE FULL GIT PATH OF REPOSITORY" to full path of the git repository ending with .git
    - default: main to the branch in the private git repo. 
  
   Save changes and exit.

7. Run the following command.

   ```sh 
   kubectl apply -f trigger-bringup-pipeline.yml; 
   kubectl apply -f trigger-bringup-res.yml
   ```

8. Check if the pipelines are listed by using the following command.

   ```sh
   tkn p ls
   ```

9. Perform a git commit on the branch with a commit message of "exec_bringup".

   The pipelines are triggered automatically.

[Back to Main](../README.md)

