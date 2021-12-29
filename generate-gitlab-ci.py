#!/usr/bin/env python3

_DEFAULT_DEPENDENCIES = [
    "packages/data/**/*",
    "packages/common/**/*",
    "packages/course-landing/**/*",
    "packages/{{site}}/**/*",
    "yarn.lock",
]

_COURSE_LANDING_DEPENDENCIES = [
    "packages/data/training/sessions.yml",
    "packages/data/training/recommendations/**/*",
    "packages/data/training/recommendations/**/*",
    "packages/data/training/pictures/**/*",
    "packages/common/**/*",
    "packages/course-landing/**/*",
    "packages/{{site}}/**/*",
    "yarn.lock",
]

_ONDREJSIKA_THEME_DEPENDENCIES = [
    "packages/data/**/*",
    "packages/common/**/*",
    "packages/ondrejsika-theme/**/*",
    "packages/{{site}}/**/*",
    "yarn.lock",
]


_ONDREJSIKA_SINGLEPAGE_DEPENDENCIES = _ONDREJSIKA_THEME_DEPENDENCIES + [
    "packages/ondrejsika-singlepage/**/*",
]

PROD_SITES = {
    "trainera.de": {
        "dependencies": _ONDREJSIKA_THEME_DEPENDENCIES,
        "cloudflare_workers": True,
    },
    "ondrej-sika.com": {
        "dependencies": _ONDREJSIKA_THEME_DEPENDENCIES,
        "cloudflare_workers": True,
    },
    "ondrej-sika.cz": {
        "dependencies": _ONDREJSIKA_THEME_DEPENDENCIES,
        "cloudflare_workers": True,
    },
    "ondrej-sika.de": {
        "dependencies": _ONDREJSIKA_SINGLEPAGE_DEPENDENCIES,
        "cloudflare_workers": True,
    },
    "trainera.cz": {
        "dependencies": _ONDREJSIKA_THEME_DEPENDENCIES,
        "cloudflare_workers": True,
    },
    "skolenie.kubernetes.sk": {
        "dependencies": _COURSE_LANDING_DEPENDENCIES,
    },
    "training.kubernetes.is": {
        "dependencies": _COURSE_LANDING_DEPENDENCIES,
    },
    "training.kubernetes.lu": {
        "dependencies": _COURSE_LANDING_DEPENDENCIES,
    },
    "cal-api.sika.io": {
        "dependencies": _DEFAULT_DEPENDENCIES,
    },
    "ccc.oxs.cz": {
        "dependencies": _DEFAULT_DEPENDENCIES,
    },
    "sika.blog": {
        "dependencies": _DEFAULT_DEPENDENCIES,
    },
    "static.sika.io": {
        "dependencies": _DEFAULT_DEPENDENCIES,
    },
    "sikahq.com": {
        "dependencies": _DEFAULT_DEPENDENCIES,
    },
    "ondrejsika.is": {
        "dependencies": _ONDREJSIKA_SINGLEPAGE_DEPENDENCIES,
        "cloudflare_workers": True,
    },
    "skoleni.io": {
        "dependencies": _DEFAULT_DEPENDENCIES,
        "cloudflare_workers": True,
    },
}

ALL_SITES = {}
ALL_SITES.update(PROD_SITES)

PRIORITY_SITES = (
    "ondrej-sika.cz",
    "ondrej-sika.com",
    "trainera.cz",
    "skoleni.io",
    "trainera.de",
)
SUFFIX = ".panda.k8s.oxs.cz"
SITES = ALL_SITES.keys()

out = []
out.append(
    """# Don't edit this file maually
# This file is generated by ./generate-gitlab-ci.py

image: ondrejsika/ci

stages:
  - start
  - build_docker_priority
  - deploy_dev_priority
  - deploy_prod_priority
  - build_docker
  - deploy_dev
  - deploy_prod

variables:
  DOCKER_BUILDKIT: '1'
  GIT_CLEAN_FLAGS: "-ffdx -e node_modules"

start:
  stage: start
  script: echo "start job - you can't create empty child pipeline"
"""
)


def generate_dependencies(site):
    if site not in ALL_SITES:
        return """      - packages/data/**/*
      - packages/common/**/*
      - packages/course-landing/**/*
      - packages/{{site}}/**/*
      - yarn.lock""".replace(
            "{{site}}", site
        )
    return "\n".join(
        ("      - " + line).replace("{{site}}", site)
        for line in ALL_SITES[site]["dependencies"]
    )


for site in SITES:
    if site in ALL_SITES and ALL_SITES[site].get("cloudflare_workers"):
        pass
    else:
        out.append(
            """
%(site)s build docker:
  stage: build_docker%(priority_suffix)s
  image: ondrejsika/ci-node-docker
  needs: []
  variables:
    GIT_CLEAN_FLAGS: none
  script:
    - yarn
    - rm -rf packages/%(site)s/out
    - yarn run static-%(site)s
    - docker login $CI_REGISTRY -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD
    - cp ci/docker/* packages/%(site)s/
    - docker build -t $CI_REGISTRY_IMAGE/%(site)s:$CI_COMMIT_SHORT_SHA packages/%(site)s
    - rm packages/%(site)s/Dockerfile
    - rm packages/%(site)s/nginx-site.conf
    - docker push $CI_REGISTRY_IMAGE/%(site)s:$CI_COMMIT_SHORT_SHA
  except:
    variables:
      - $EXCEPT_BUILD
      - $EXCEPT_BUILD_DOCKER
  only:
    changes:
%(dependencies)s
"""
            % {
                "site": site,
                "priority_suffix": "_priority" if site in PRIORITY_SITES else "",
                "dependencies": generate_dependencies(site),
            }
        )

    if site in PROD_SITES:
        if PROD_SITES[site].get("cloudflare_workers"):
            out.append(
                """
%(site)s prod deploy cloudflare:
  image: sikalabs/extra:node-with-slu
  stage: deploy_prod%(priority_suffix)s
  script:
    - yarn
    - yarn add @cloudflare/wrangler -W
    - rm -rf packages/%(site)s/out
    - mkdir -p packages/%(site)s/public/api
    - slu static-api version > packages/%(site)s/public/api/version.json
    - yarn run deploy-%(site)s
  except:
    variables:
      - $EXCEPT_DEPLOY
      - $EXCEPT_DEPLOY_K8S
      - $EXCEPT_DEPLOY_PROD
      - $EXCEPT_DEPLOY_PROD_K8S
  only:
    refs:
      - master
    changes:
%(dependencies)s
  environment:
    name: k8s/prod/%(site)s
    url: https://%(site)s
  dependencies: []
"""
                % {
                    "site": site,
                    "suffix": SUFFIX,
                    "name": site.replace(".", "-"),
                    "priority_suffix": "_priority" if site in PRIORITY_SITES else "",
                    "dependencies": generate_dependencies(site),
                }
            )
        else:
            out.append(
                """
%(site)s prod deploy k8s:
  needs:
    - %(site)s build docker
  stage: deploy_prod%(priority_suffix)s
  variables:
    GIT_STRATEGY: none
    KUBECONFIG: .kubeconfig
  script:
    - echo $KUBECONFIG_FILECONTENT | base64 --decode > .kubeconfig
    - helm repo add ondrejsika https://helm.oxs.cz
    - helm upgrade --install %(name)s ondrejsika/one-image --set host=%(site)s --set image=$CI_REGISTRY_IMAGE/%(site)s:$CI_COMMIT_SHORT_SHA --set changeCause=job-$CI_JOB_ID
    - kubectl rollout status deploy %(name)s
  except:
    variables:
      - $EXCEPT_DEPLOY
      - $EXCEPT_DEPLOY_K8S
      - $EXCEPT_DEPLOY_PROD
      - $EXCEPT_DEPLOY_PROD_K8S
  only:
    refs:
      - master
    changes:
%(dependencies)s
  environment:
    name: k8s/prod/%(site)s
    url: https://%(site)s
  dependencies: []
"""
                % {
                    "site": site,
                    "suffix": SUFFIX,
                    "name": site.replace(".", "-"),
                    "priority_suffix": "_priority" if site in PRIORITY_SITES else "",
                    "dependencies": generate_dependencies(site),
                }
            )

with open(".gitlab-ci.generated.yml", "w") as f:
    f.write("".join(out))
