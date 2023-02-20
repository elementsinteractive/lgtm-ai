# Instructions

![](/media/tutorial.mp4)


1. Configure the Gitlab Repository [following this guide](https://namespace.gitlab.io/elements/backend/pypackage-skeleton/developers-guide/getting-started/#gitlab-setup). Specifically, you need a **TEMPLATE_TOKEN** and to give permissions to the generated bot to push to the `main` branch.
2. Run the pipeline to generate your app. Go to **Build** > **Pipelines** > **Run pipeline**


## Explanation
This template works as a bootstrap project for our  💀 [pypackage-skeleton](https://gitlab.com/namespace/elements/backend/pypackage-skeleton). This repository is, at the moment, almost empty. It simply contains a [pipeline](./.gitlab-ci.yml). 

This pipeline, when executed, will run the cruft template of pypackage-skeleton with the provided parameters and will replace the contents of this repository with the result of that template run. This will mark the start of your new project, which will be up to date with the pypackage-skeleton.

This template runner is supposed to work with Gitlab's Project Templates functionality (see video tutorial above).
