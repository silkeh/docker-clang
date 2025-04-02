#!/usr/bin/env python3

import os
import os.path
import requests
import yaml
import argparse
import subprocess


def replace(s, version, debian_version, architecture='', packages='', repo=None):
    if repo is not None:
        s = s.\
            replace('{repo_url}', repo.url).\
            replace('{repo_distribution}', repo.distribution).\
            replace('{repo_component}', repo.component)

    return s.\
        replace('{packages}', packages).\
        replace('{version}', version).\
        replace('{debian_version}', debian_version).\
        replace('{architecture}', architecture)


def get(d, key):
    return d.get(key, d['default'])


class Replacer:
    def __init__(self, version, debian_version, architecture='', packages=''):
        self.version = version
        self.debian_version = debian_version
        self.architecture = architecture
        self.packages = packages

    def replace(self, s):
        return replace(s, self.version, self.debian_version, self.architecture, self.packages)


class DebianRepo:
    def __init__(self, url, distribution, component):
        self.url = url
        self.distribution = distribution
        self.component = component

    def architectures(self, architectures):
        return [a for a in architectures if self._exists(a)]

    def _exists(self, architecture):
        res = requests.get(self._release_url(architecture))
        if res.status_code == 200:
            return True

        if res.status_code == 404:
            return False

        raise Exception(f'Unexpected status code: {res.status_code}')

    def _release_url(self, architecture):
        return f'{self.url}/dists/{self.distribution}/{self.component}/binary-{architecture}/Release'


class Builder:
    UNSTABLE = ['unstable']

    def __init__(self, config):
        self.repo_url = config['repo_url']
        self.repo_distributions = config['repo_distributions']
        self.repo_component = config['repo_component']
        self.versions = config['versions']
        self.packages = config['packages']
        self.debian_architectures = config['debian_architectures']
        self.debian_versions = config['debian_versions']
        self.docker_platforms = config['docker_platforms']
        self.environments = config['environments']
        self.environment = self.environments[0]
        self._dockerfiles = []

    def _repo_distributions(self, version):
        return get(self.repo_distributions, version)

    def _find_repo(self, version, debian_version, architectures):
        for distribution in self._repo_distributions(version):
            repl = Replacer(version, debian_version)
            repo = DebianRepo(repl.replace(self.repo_url),
                              repl.replace(distribution),
                              repl.replace(self.repo_component))
            arch = repo.architectures(architectures)
            if len(arch) > 0:
                return repo, arch

        return None, None

    def _architectures(self, debian_version):
        return get(self.debian_architectures, debian_version)

    def _platforms(self, architectures):
        return [self.docker_platforms[a] for a in architectures]

    def _packages(self, version):
        return get(self.packages, version)

    def _new_dockerfile(self, version, debian_version, repo, architectures):
        d = Dockerfile(version, debian_version, repo,
                       self._platforms(architectures), self._packages(version))

        self._dockerfiles.append(d)

        return d

    def _get_dockerfiles(self):
        if len(self._dockerfiles) > 0:
            for d in self._dockerfiles:
                yield d

            return

        for version in self.versions:
            for debian_version in self.debian_versions:
                if self._skip_version(version, debian_version):
                    print(f'Skipping: {version}-{debian_version}')
                    continue

                repo, architectures = self._find_repo(version, debian_version,
                                                      self._architectures(debian_version))
                if repo is None:
                    print(f'No repo: {version}-{debian_version}')
                    continue

                yield self._new_dockerfile(version, debian_version, repo, architectures)

    def _skip_version(self, version, debian_version):
        return \
            self._skip_dev_release(version, debian_version) or \
            self._skip_unstable_release(version, debian_version)

    def _skip_dev_release(self, version, debian_version):
        return version == 'dev' and \
            debian_version not in (self.UNSTABLE + self.debian_versions[-1:])

    def _skip_unstable_release(self, version, debian_version):
        return version != 'dev' and \
            version not in self.versions[-2:] and \
            debian_version in self.UNSTABLE

    def dockerfiles(self):
        return list(self._get_dockerfiles())

    def generate(self):
        for dockerfile in self._get_dockerfiles():
            print(f"Creating: {dockerfile.tag}")
            dockerfile.create()

    def build(self, name: str):
        for dockerfile in self._get_dockerfiles():
            print(f"Building: {dockerfile.tag}")
            dockerfile.create()
            dockerfile.build(name)

    def buildx(self, name: str):
        for dockerfile in self._get_dockerfiles():
            print(f"Cross-building: {dockerfile.tag} ({', '.join(dockerfile.platforms)})")
            dockerfile.create()
            dockerfile.buildx(name)

    def _latest(self):
        dockerfiles = list(self._get_dockerfiles())
        if len(dockerfiles) == 0:
            raise Exception('No docker files')

        return dockerfiles[-1].tag

    def _latest_version(self, v: str):
        dockerfiles = [d for d in self._get_dockerfiles() if d.version == v]
        if len(dockerfiles) == 0:
            return None

        return dockerfiles[-1].tag

    def _latest_versions(self):
        versions = {v: self._latest_version(v) for v in self.versions}
        return {v: l for v, l in versions.items() if l is not None}

    def aliases(self):
        return self._latest_versions() | {
            'latest': self._latest(),
        }

    def environment_aliases(self):
        tags = [d.tag for d in builder.dockerfiles()]
        aliases = [tag for tag in builder.aliases()]

        return [(env, tag)
                for tag in (tags + aliases)
                for env in self.environments]

    def tag_aliases(self, name: str):
        for alias, tag in self.aliases().items():
            print(f'Tagging {tag} as {alias}')

            r = subprocess.run(['docker', 'tag', f'{name}:{tag}', f'{name}:{alias}'])
            if r.returncode != 0:
                raise Exception('Error')


class Dockerfile:
    def __init__(self, version, debian_version, repo, platforms, packages):
        self.version = version
        self.debian_version = debian_version
        self.repo = repo
        self.platforms = platforms
        self.packages = packages

    def create(self):
        with open(self._path, 'w') as f:
            f.write(replace(
                self._template(),
                self.version,
                self.debian_version,
                packages=' '.join(self.packages),
                repo=self.repo
            ))

    def build(self, name: str):
        r = subprocess.run(['docker', 'build', '.',
                            '--file', self._path,
                            '--tag', f'{name}:{self.tag}'])
        if r.returncode != 0:
            raise Exception('Build failed')

    def test(self, name: str):
        r = subprocess.run(['docker', 'run', '--tty',
                            '--volume', os.getcwd() + '/tests:/tests',
                            f'{name}:{self.tag}', '/tests/run.sh', self.version])
        if r.returncode != 0:
            raise Exception('Test failed')

    def buildx(self, name: str):
        r = subprocess.run(['docker', 'buildx', 'build', '.',
                            '--target', 'test',
                            '--cache-from', 'type=local,src=/tmp/buildx',
                            '--cache-to', 'type=local,dest=/tmp/buildx,mode=max',
                            '--file', self._path,
                            '--platform', ','.join(self.platforms),
                            '--tag', f'{name}:{self.tag}'])
        if r.returncode != 0:
            raise Exception('Cross-platform build failed')

    @property
    def tag(self):
        return f'{self.version}-{self.debian_version}'

    @property
    def _path(self):
        return os.path.join('dockerfiles', f'{self.version}-{self.debian_version}.Dockerfile')

    def _template(self):
        path = \
            self._template_path_version_debian_version() or \
            self._template_path_version() or \
            self._template_path_debian_version() or \
            self._template_path('debian')

        with open(path) as f:
            return f.read()

    def _template_path_version_debian_version(self):
        path = self._template_path(f'{self.version}-{self.debian_version}')
        if os.path.exists(path):
            return path

        return None

    def _template_path_debian_version(self):
        path = self._template_path(self.debian_version)
        if os.path.exists(path):
            return path

        return None

    def _template_path_version(self):
        path = self._template_path(self.version)
        if os.path.exists(path):
            return path

        return None

    def _template_path(self, name):
        return os.path.join('templates', name + '.Dockerfile')


class GitLabCI:
    def __init__(self, data):
        self.data = data

    def generate(self, dockerfiles, aliases, env_aliases):
        self.add_dockerfiles(dockerfiles)
        self.add_aliases(aliases)
        self.add_environments(env_aliases)
        self.save()

    def add_aliases(self, aliases):
        for alias, tag in aliases.items():
            self.data[alias] = {
                'extends': '.alias',
                'needs': [tag],
                'variables': {
                    'DST_TAG': alias,
                    'SRC_TAG': tag
                }
            }

    def add_dockerfiles(self, dockerfiles):
        for dockerfile in dockerfiles:
            self.data[dockerfile.tag] = {
                'extends': GitLabCI._extends(dockerfile),
                'variables': {
                    'IMAGE_TAG': dockerfile.tag,
                    'CLANG_VERSION': dockerfile.version,
                    'PLATFORMS': ','.join(dockerfile.platforms),
                }
            }

    def add_environments(self, env_aliases):
        for env, tag in env_aliases:
            self.data[f"{tag} ({env})"] = {
                'extends': '.environment-alias',
                'needs': [tag],
                'environment': {
                    'name': env,
                },
                'variables': {
                    'SRC_TAG': tag,
                    'DST_TAG': tag,
                }
            }

    def save(self):
        with open(os.path.join('dockerfiles', 'gitlab-ci.yml'), 'w') as f:
            f.write(yaml.dump(self.data))

    @staticmethod
    def _extends(dockerfile):
        if dockerfile.platforms == ['linux/amd64']:
            return '.docker'

        return '.docker-buildx'


if __name__ == '__main__':
    ci_template_file = os.path.join('templates', 'gitlab-ci.yml')

    parser = argparse.ArgumentParser(description='Generate and build docker files')
    parser.add_argument('-c', '--config', default='config.yaml',
                        help='Config file')
    parser.add_argument('-i', '--image', default='silkeh/clang',
                        help='Image name')
    parser.add_argument('-t', '--ci-template', default=ci_template_file,
                        help='GitLab CI template')
    parser.add_argument('-v', '--version', default=[], action='append',
                        help='LLVM version to build, all by default')
    parser.add_argument('-d', '--debian', default=[], action='append',
                        help='Debian version to build, all by default')
    parser.add_argument('command', choices=['ci', 'alias', 'generate', 'build', 'buildx'],
                        help='Action to execute')

    args = parser.parse_args()

    with open(args.ci_template) as f:
        gitlab_ci = GitLabCI(yaml.safe_load(f.read()))

    with open(args.config) as f:
        builder = Builder(yaml.safe_load(f.read()))

    if len(args.version) > 0:
        builder.versions = args.version

    if len(args.debian) > 0:
        builder.debian_versions = args.debian

    match args.command:
        case "ci":
            builder.generate()
            gitlab_ci.generate(builder.dockerfiles(),
                               builder.aliases(),
                               builder.environment_aliases())
        case "build":
            builder.build(args.image)
            builder.tag_aliases(args.image)
        case "buildx":
            builder.buildx(args.image)
        case "generate":
            builder.generate()
        case "alias":
            builder.tag_aliases(args.image)
