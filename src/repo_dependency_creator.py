"""Helper class to create repository and it's respective dependency nodes in graph DB."""

import requests

from utils import GREMLIN_SERVER_URL_REST, fix_gremlin_output


class RepoDependencyCreator:
    """Finds out direct and indirect dependencies from a given github repository."""

    # TODO: refactor this static method so it will be possible to test it properly
    @staticmethod
    def create_repo_node_and_get_cve(github_repo, deps_list):
        """Create a repository node in the graphdb and create its edges to all deps.

        :param github_repo: git repository for scanning
        :param deps_list: dependency list for scanning
        """
        gremlin_str = ("repo=g.V().has('repo_url', '{repo_url}').tryNext().orElseGet{{"
                       "graph.addVertex('vertex_label', 'Repo', 'repo_url', '{repo_url}')}};"
                       "g.V(repo).outE('has_dependency').drop().iterate();"
                       "g.V(repo).outE('has_transitive_dependency').drop().iterate();".format(
                        repo_url=github_repo))

        # Create an edge between repo -> direct dependencies
        for pkg in deps_list.get('direct'):
            if len(pkg.split(':')) == 4:
                ecosystem, group_id, artifact_id, version = pkg.split(':')
            else:
                ecosystem, group_id, version = pkg.split(':')
            name = group_id + ':' + artifact_id if group_id and artifact_id \
                else group_id
            gremlin_str += ("ver=g.V().has('pecosystem', '{ecosystem}').has('pname', '{name}')."
                            "has('version', '{version}');ver.hasNext() && "
                            "g.V(repo).next().addEdge('has_dependency', ver.next());".format(
                                ecosystem=ecosystem, name=name, version=version))

        # Create an edge between repo -> transitive dependencies
        for pkg in deps_list.get('transitive'):
            if len(pkg.split(':')) == 4:
                ecosystem, group_id, artifact_id, version = pkg.split(':')
            else:
                ecosystem, group_id, version = pkg.split(':')
            name = group_id + ':' + artifact_id if group_id and artifact_id \
                else group_id
            gremlin_str += ("ver=g.V().has('pecosystem', '{ecosystem}').has('pname', '{name}')."
                            "has('version', '{version}');ver.hasNext() && "
                            "g.V(repo).next().addEdge('has_transitive_dependency', ver.next());"
                            .format(ecosystem=ecosystem, name=name, version=version))

        # Traverse the Repo to Direct/Transitive dependencies that have CVE's and report them
        gremlin_str += (
            "g.V(repo).as('rp').outE('has_dependency','has_transitive_dependency')"
            ".as('ed').inV().as('epv').out('has_cve').as('cve')"
            ".select('rp','ed','epv','cve').by(valueMap(true));"
        )
        payload = {"gremlin": gremlin_str}
        try:
            rawresp = requests.post(url=GREMLIN_SERVER_URL_REST, json=payload)
            resp = rawresp.json()
            if rawresp.status_code != 200:
                raise Exception("Error creating repository node for {repo_url} - "
                                "{resp}".format(repo_url=github_repo, resp=resp))

        except Exception:
            raise Exception(
                "Error creating repository node for {repo_url}".format(repo_url=github_repo))

        return fix_gremlin_output(resp)

    @staticmethod
    def generate_report(repo_cves, deps_list):
        """
        Generate a json structure to include cve details for dependencies.

        :param repo_cves: CVEs found in the repository
        :param deps_list: Dependency list
        :return: list
        """
        repo_list = []
        for repo_cve in repo_cves.get('result').get('data', []):
            epv = repo_cve.get('epv')
            repo_url = repo_cve.get('rp').get('repo_url')[0]
            name = epv.get('pname')[0]
            version = epv.get('version')[0]
            ecosystem = epv.get('pecosystem')[0]
            str_epv = ecosystem + ":" + name + ":" + version
            cves = repo_cve.get('cves', [])
            vulnerable_deps = []
            first = True
            if cves and (str_epv in i for x, i in deps_list.items()):
                cve_list = []
                for cve in cves:
                    cve_list.append(
                        {'CVE': cve.get('cve_id')[0], 'CVSS': cve.get('cvss_v2', [10.0])[0]}
                    )
                vulnerable_deps.append({
                    'ecosystem': epv.get('pecosystem')[0],
                    'name': epv.get('pname')[0],
                    'version': epv.get('version')[0],
                    'cve_count': len(cves), 'cves': cve_list,
                    'is_transitive': repo_cve.get('ed').get('label') == 'has_transitive_dependency'
                })

            for repo in repo_list:
                if repo_url == repo.get('repo_url'):
                    repo_vul_deps = repo.get('vulnerable_deps')
                    repo['vulnerable_deps'] = vulnerable_deps + repo_vul_deps
                    first = False
            if first:
                repo_list.append({'repo_url': repo_url, 'vulnerable_deps': vulnerable_deps})

        return repo_list
