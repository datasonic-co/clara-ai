/* groovylint-disable DuplicateStringLiteral, LineLength */

/* Get Env Letter */
def replaceEnv(branchName) {
    if ('tia_chainlit/dev'.equals(branchName)) {
        return '-dev'
    }
    else if ('tia_chainlit/staging'.equals(branchName)) {
        return '-staging'
    }
    else if ('tia_chainlit/master'.equals(branchName)) {
        return ''
    }
    else
        return '-test'

}

def getReplicaByEnv(branchName) {
   if ('tia_chainlit/master'.equals(branchName)) {
        return '2'
   }
   else
      return '1'
}

/* Get Env Letter */
def getEnv(branchName) {
    if ('tia_chainlit/dev'.equals(branchName)) {
        return 'Dev'
    }
    else if ('tia_chainlit/staging'.equals(branchName)) {
        return 'Staging'
    }
    else if ('tia_chainlit/master'.equals(branchName)) {
        return 'Production'
    }
    else
        return 'Test'

}

//Get version from CHANGELOG.md
def getVersionFromToml() {

   version = sh(returnStdout: true, script: """grep -oP 'version\\s*=\\s*"[0-9]+\\.[0-9]+\\.[0-9]+"' container/ai-assistant/app/pyproject.toml | awk -F '=' '
   {print \$2}' | tr -d '"'
   """).trim()
   return version
}


def tsToHumanDate(timestamp) {
    Date date = new Date(timestamp)
    return date.format("yyyy-MM-dd HH:mm:ss")
}

def isBuildable(branch) {
    return branch in ["tia_chainlit/master"]
}

pipeline {
   agent {
      docker {
         label 'openshift'
         image 'tools/python/python3.9.16:2.5'
      }
   }

    triggers {
        GenericTrigger (
            genericVariables: [
                [key: 'REQUESTER', value: '$.actor.displayName'],
                [key: 'BRANCH', value: '$.changes[0].ref.displayId'],
                [key: 'BODY', value: '$']
            ],
            token: 'lkalkazelaz',
            causeString: 'Triggered by $REQUESTER',
            printContributedVariables: true,
            printPostContent: true,
        )
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '5'))
        disableConcurrentBuilds()
        skipStagesAfterUnstable()
        timeout(time: 30, unit: 'MINUTES')   // timeout on whole pipeline job
    }

   parameters {
        string(name: 'REQUESTER', description: 'Build requester', trim: true, defaultValue: 'auto')
        string(name: 'MAILING_LIST', description: 'Mailing list to report', trim: true, defaultValue: 'fakher.hannafi.prestataire@bpce-it.fr')
        string(name: 'BRANCH', description: 'Branch to build', trim: true, defaultValue: 'master')
        booleanParam(name: 'BUILD', defaultValue: true, description: 'Build a new image')
        booleanParam(name: 'PROMOTE', defaultValue: true, description: 'Push image to prod')
        booleanParam(name: 'DEPLOY', defaultValue: true, description: 'Deploy to OCP')
   }

   environment {
      IMAGE_VER = getVersionFromToml()
      // BRANCH = "$BRANCH"
      def start_date = tsToHumanDate(currentBuild.startTimeInMillis)
   }

   stages {
      stage('Init Env Vars') {
         // when {
         //       expression { isBuildable(GIT_BRANCH) }
         // }
         steps {
            script {
               echo "${GIT_BRANCH}"
               echo "${getVersionFromToml()}"
               def loadenv = load "vars.groovy"
               loadenv.loadenv()
            }
         }
      }

      // stage('Build Python wheel') {
      //    when {
      //          expression { isBuildable(GIT_BRANCH) }
      //    }
      //    environment {
      //       IMG="container/${IMAGE_NAME}/app"
      //    }
      //    steps {
      //      sh """
      //          cd $IMG
      //          python -m pip install 'build<0.10.0'
      //          python -m build --wheel
      //      """
      //    }
      // }

      stage('Prebuild') {
         when {
               expression { isBuildable(GIT_BRANCH) }
         }
         environment {
            ARTIFACTORY_CREDS = credentials("${ARTIFACTORY_USER}")
            IMAGE_NAME = "$env.IMAGE_NAME"
         }
      
         steps {
           sh """
            curl -u ${ARTIFACTORY_CREDS} "https://${ARTIFACTORY_URL}:443/artifactory/tia-generic-tia-prv-p/openshift/cli/oc" -O --insecure
            mkdir -p container/${IMAGE_NAME}/bin
            mv oc container/${IMAGE_NAME}/bin
           """
         }
      }

      stage('build-image') {
         when {
               expression { isBuildable(GIT_BRANCH) }
         }
         environment {
            ARTIFACTORY_CREDS = credentials("${ARTIFACTORY_USER}")
            OCP_APPLICATION_NAME="tia-image-openshift"
            IMG="container/${IMAGE_NAME}"
         }
         steps {
            withCredentials([usernamePassword(credentialsId: "openshift_token_hpr", usernameVariable: 'OCP_BUILDER_NAMESPACE', passwordVariable: 'OCP_BUILDER_TOKEN')]) {
               sh """
               echo ${env.STATUS_CODE}
               cd $IMG

               cp /etc/localtime .

               echo "Logging to openshift"
               export KUBECONFIG=container/.kube/config
               oc login ${OCP_SERVER_HPR} --token=${OCP_BUILDER_TOKEN} --insecure-skip-tls-verify=true

               echo "Switching to builder namespace"
               oc project "${OCP_BUILDER_NAMESPACE}"

               echo "preparing build configuration"
               oc new-build --name="${OCP_APPLICATION_NAME}-builder-${IMAGE_NAME}-${BUILD_NUMBER}" \
                  --to="${ARTIFACTORY_REGISTRY}.${ARTIFACTORY_URL}/${IMAGE_NAME}:${IMAGE_VER}" \
                  --to-docker=true \
                  --strategy=docker \
                  --binary=true \
                  --push-secret="${OCP_BUILDER_NAMESPACE}-dockersecret-push"

               echo "patch build config to 2 Go of Memory, 2 CPU cores"
               oc patch bc "${OCP_APPLICATION_NAME}-builder-${IMAGE_NAME}-${BUILD_NUMBER}" --patch '{"spec":{"resources":{"limits":{"memory":"2Gi", "cpu":2} } } }'

               echo "Replace Version in Dockerfile"
               sed -i "s#VERSION#${IMAGE_VER}#g" Dockerfile

               echo "Starting Build and pushing image to artifactory"
               oc start-build "${OCP_APPLICATION_NAME}-builder-${IMAGE_NAME}-${BUILD_NUMBER}" --from-dir . --wait --follow

               echo "Delete Build config once finished"
               oc delete bc "${OCP_APPLICATION_NAME}-builder-${IMAGE_NAME}-${BUILD_NUMBER}"
               """
            }
         }
      }

      stage('promote-image') {
         when {
               expression { isBuildable(GIT_BRANCH) }
         }

         // when {
         //    expression { return env.STATUS_CODE != '200'}
         // }

         environment {
            ARTIFACTORY_CREDS = credentials("${ARTIFACTORY_USER}")
         }

         steps {
            sh """
            curl -X POST "https://${ARTIFACTORY_URL}:443/artifactory/api/docker/${ARTIFACTORY_REGISTRY}/v2/promote" \
            -u ${ARTIFACTORY_CREDS} \
            --header 'Content-Type: application/json' \
            --insecure \
            --data '{
               "targetRepo" : "${ARTIFACTORY_PROD}",
               "dockerRepository" : "${IMAGE_NAME}",
               "targetDockerRepository" : "${IMAGE_NAME}",
               "tag" : "${IMAGE_VER}",
               "targetTag" : "${IMAGE_VER}",
               "copy": true
            }'
            """
         }
      }

      stage('deploy release') {
         when {
            expression {
               return params.DEPLOY && isBuildable(GIT_BRANCH)
            }
         }

         environment {
            OCP_APPLICATION_NAME="tia-image-openshift"
         }

         steps {
            withCredentials([usernamePassword(credentialsId: "openshift_token_hubble", usernameVariable: 'OCP_BUILDER_NAMESPACE', passwordVariable: 'OCP_BUILDER_TOKEN')]) {

            sh """

               echo "Logging to openshift"
               export KUBECONFIG=container/.kube/config
               oc login ${OCP_SERVER_PRD} --token=${OCP_BUILDER_TOKEN} --insecure-skip-tls-verify=true

               echo "Switching to builder namespace"
               oc project "${OCP_BUILDER_NAMESPACE}"

               echo "Update with the new version"
               sed -i "s#IMAGE_VER#${IMAGE_VER}#g" infra/dep-assistant.yml

               echo "Get Env from Branch Name"
               sed -i "s#ENV#${replaceEnv(GIT_BRANCH)}#g" infra/dep-assistant.yml

               echo "Get Env from Branch Name"
               sed -i "s#NUM_REPLICAS#${getReplicaByEnv(GIT_BRANCH)}#g" infra/dep-assistant.yml


               export KUBECONFIG=container/.kube/config
               echo "Apply new config in deployment"
               oc apply -f infra/dep-assistant.yml
            """
            }
         }
      }
   }

    post {
        always {
            cleanWs()
            dir("${env.WORKSPACE}@tmp") {
                deleteDir()
            }
            dir("${env.WORKSPACE}@2") {
                deleteDir()
            }
            dir("${env.WORKSPACE}@2@tmp") {
                deleteDir()
            }
        }
        failure {
            emailext (
                subject: "FAILED Job '${env.JOB_NAME}, Build [${env.BUILD_NUMBER}] Triggered by ${REQUESTER}' ",
                body: """<html>
                        <body>
                           <h1 style="color: red;">Build FAILED!</h1>
                           <p style="color: black;">Build details:</p>
                           <ul>
                           <li><b>Job:</b> ${env.JOB_NAME}</li>
                           <li><b>Build Number:</b> ${env.BUILD_NUMBER}</li>
                           <li><b>Build Url:</b> <a href="${env.BUILD_URL}">${env.BUILD_URL}</a></li>
                           <li><b>Start Time:</b> ${start_date}</li>
                           <li><b>Duration:</b> ${currentBuild.durationString}</li>
                           <li><b>Used Branch: </b> ${GIT_BRANCH}</li>
                           <li><b>Bitbucket Url:</b> <a href="${GIT_URL}">${GIT_URL}</a></li>
                           </ul>
                        </body>
                        </html>""",
                to: "$MAILING_LIST",
                mimeType: 'text/html'
            )
        }
        success {
         script {

            if (isBuildable(GIT_BRANCH)){
                emailext (
                    subject: "New Release for '${env.JOB_NAME}, Build [${env.BUILD_NUMBER}] By ${REQUESTER}' ",
                    body: """<html>
                        <body>
                            <h1 style="color: green;">Build & Deploy Successful!</h1>
                            <p style="color: black;">Hi there</p>
                            <p style="color: black;">Details:</p>
                            <ul>
                            <li><b>Job:</b> ${env.JOB_NAME}</li>
                            <li><b>Deployed Environment</b> ${getEnv(GIT_BRANCH)}</li>
                            <li><b>Release Number:</b> ${IMAGE_VER}</li>
                            <li><b>Start Time:</b> ${start_date}</li>
                            <li><b>Duration:</b> ${currentBuild.durationString}</li>
                            </ul>
                        </body>
                        </html>""",
                    to: "$MAILING_LIST",
                    mimeType: 'text/html'
                )
            }

         }

        }
    }
}