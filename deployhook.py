import hmac
import hashlib
import os
import tempfile
import subprocess
from contextlib import contextmanager
from flask import Flask, request, jsonify


app = Flask(__name__)

IS_DEV = (app.env == 'development')

GETSENTRY_OWNER = 'getsentry'
SENTRY_REPO = '{}/sentry'.format(GETSENTRY_OWNER)

DEPLOY_MARKER = '#sync-getsentry'

DEPLOY_REPO = 'git@github.com:getsentry/getsentry'
DEPLOY_BRANCH = 'master'
COMMITTER_NAME = 'Sentry Bot'
COMMITTER_EMAIL = 'bot@getsentry.com'
SSH_KEY = '''
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA5UH9KUvBAx/Y6pB+UFyi3dWxbnlKgzRD2I58VnosBhJMk5b/
Lc+5L7cNaNbitznOm+9cnyLEBKwWPl2Do01Zq2whamFph+tb8cKe+qhqix7aqOFq
1PgTduTlAHiHzVD22jasUKqDDA9hFTY5qn1q/v/rIjoErZ7bv0g8JjK3j941yfpi
K8cNN/EQslRgziPRARNauQt8CoCCnKsphMWUvIkzdMCAjskwtBQBB56ii+tTChHj
YXuMIQW8PQ1JPZk+iAwwU66/n/Oi5NPldC9aTgNwLKEnjfi61QCq/Op6qmvNv6Zf
Rdge8JCI8MTLmfD8mVM/tDesChtAwTP6vSX2owIDAQABAoIBAD5eTmX+otqbvmJJ
vuNT4EbjTKrWOmwpOs/eK3tHL1TTg5ufN3qaCTIu5WoBE5pvEoMfgh4U0ijHPCHp
RNeXQm69MvYC3DfK0q+Zl7BvQtToJupMsMiRWJI+wQH4yFEV1qIUv5oOWSpdwLaJ
kvSLvCD1NF2SVRV6oyONnjdyErgDYtQyjKv6jJo6HY3a7CwdiCTcKX0j7+v1/i8C
Ourkdk/ON63Pv+rY2eOJetbJ0er0Dg688qmayFfrfzh3i6tShDn5YY/RuqE5L4ZH
YX30klIxLPLS7dWseKrdB7ZlyIWDtmVVWcCctKJcZUYk46Ofjxkyyyig6b7HeH3C
kBUhrzECgYEA+ep2pDrA64uVqWMpIeby8RumuJ+TCIVY2uo9pjVDmK2RZKmzH0Rd
2K29TZVcEeOFQxFAFu7RFRJfO/4zz93mE5rvu5J0Nv/50j61IC5diAeXwpkqtIw5
bFbuws4/9pm4D4DmPe4Rio/hv32zNmbijzY2vuzlH3dlWWGRxnmempsCgYEA6tbH
dYmnK2lgyorLIO+jVn4qw+GJm+I6kDTMVp/weKinuQZrRmccdhm7XSlWYlq/YyPd
2qevl4MSjDFBV60Pvoaf+TIns/0YHYhe15M9jNrAotJIkGA8rmc+e3PeF95i2RD+
QkDd+wp5Hp37+edMIVyYFSeU6MnjPpWmZi3DsJkCgYEAySeNIxcfXPfXGKX135HS
jXriMMxQPpWGNX5A7N0GcYeS9WEaCdqvZs5BBodnugZVpuvlmA/VPo6xFMrAzVkf
7TvSJjn1TKewXyeWBjcLlYf3AOzj0LrlJWy7dRUpqsWDvwbTS5mpiMvSupzkeK9L
QFY0rmxi53bknpLIEOanYG0CgYBoBuJuP57szQ5SSm821NCvFM6O3M6fXfSBQtIt
oUXdvSAnBx/oHO7vpfBokVIx2W8kVJQHMvbGkApcTclbNE9gH7Snp78MrRXMp0cU
CaZfSdvBhJMeWXMn8pYsC6SbQCjbbPqkkKWEehwzItqm1f3UXXcFD/aXtC7U32fJ
pYYlKQKBgDdHJvVhrJpYNm7wNO029Bhpoon1S24Ay2cXMn9qELO11ldjJHb0Ya/c
l+nAD0p19zmc+PZzGZtbiLjD/zya0sE6+JguKaVw9iNQIlyeWXPpIpWJb4O9SbTM
2bBr3gp9Ug5GhLIAC7577QDU6L8lj6o7RJ21cKH/7M8j3OskF1V+
-----END RSA PRIVATE KEY-----
'''

PLUGIN_REPOS = [
    'getsentry/sentry-plugins',
    'getsentry/sentry-auth-saml2',
    'getsentry/sentry-auth-google',
    'getsentry/sentry-auth-github',
]

GITHUB_WEBHOOK_SECRET = os.environ.get('GITHUB_WEBHOOK_SECRET')


@contextmanager
def ssh_environment():
    key_file = tempfile.mktemp()
    with open(key_file, 'w') as f:
        f.write(SSH_KEY)
    os.chmod(key_file, 0o600)

    exec_file = tempfile.mktemp()
    with open(exec_file, 'w') as f:
        f.write('''#!/bin/sh
        ssh -i "%s" -o StrictHostKeyChecking=no "$@"
        ''' % key_file)
    os.chmod(exec_file, 0o700)
    yield exec_file


def bump_version(branch, script, *args):
    with ssh_environment() as ssh_executable:
        repo_root = tempfile.mkdtemp()

        def cmd(*args, **opts):
            opts.setdefault('cwd', repo_root)
            env = opts.setdefault('env', {})
            env['GIT_SSH'] = ssh_executable
            return subprocess.Popen(list(args), **opts).wait()

        # The branch has to be created manually in getsentry/getsentry!
        if cmd('git', 'clone', '--depth', '1', '-b', branch,
               DEPLOY_REPO, repo_root, cwd=None) != 0:
            return False, 'Cannot clone branch {} from {}.'.format(branch, DEPLOY_REPO)

        cmd('git', 'config', 'user.name', COMMITTER_NAME)
        cmd('git', 'config', 'user.email', COMMITTER_EMAIL)
        cmd(script, *args)
        for _ in range(5):
            if cmd('git', 'push', 'origin', branch) == 0:
                break
            cmd('git', 'pull', '--rebase', 'origin', branch)

        return True, 'Executed: {}'.format(' '.join([script] + list(args)))


def process_push():
    """Handle "push" events to master branch"""
    branches = set('refs/heads/' + x for x in
                   (request.args.get('branches') or 'master').split(','))

    data = request.get_json()

    if data.get('ref') not in branches:
        return jsonify(updated=False, reason='Commit against untracked branch.')

    repo = data['repository']['full_name']
    head_commit = data.get('head_commit', {})
    ref_sha = head_commit.get('id')

    # Original author will be displayed as author in getsentry/getsentry
    author_data = head_commit.get('author', {})
    author_name = author_data.get('name')
    author_email = author_data.get('email')
    if author_name and author_email:
        author = u"{} <{}>".format(author_name, author_email).encode('utf8')
    else:
        author = None

    if ref_sha is not None:
        args = [ref_sha]
        if author is not None:
            args += ['--author', author]

        if repo == SENTRY_REPO:
            updated, reason = bump_version(
                DEPLOY_BRANCH, 'bin/bump-sentry', *args
            )
        elif repo in PLUGIN_REPOS:
            args += ['--repo', repo]
            updated, reason = bump_version(
                DEPLOY_BRANCH, 'bin/bump-plugins', *args
            )
        else:
            updated = False
            reason = 'Unknown repository'
        return jsonify(updated=updated, reason=reason)

    return jsonify(updated=False, reason='Commit not relevant for deploy sync.')


def process_pull_request():
    """Handle "pull_request" events from PRs with the deploy marker set"""
    data = request.get_json()

    if data.get('action') not in ['synchronize', 'opened']:
        return jsonify(updated=False, reason='Invalid action for pull_request event.')

    if data['repository']['full_name'] != SENTRY_REPO:
        return jsonify(updated=False, reason='Unknown repository')

    # Check that the PR is from the same repo
    pull_request = data['pull_request']
    head = pull_request['head']
    base = pull_request['base']
    if head['repo']['full_name'] != SENTRY_REPO or base['repo']['full_name'] != SENTRY_REPO:
        return jsonify(updated=False, reason='Invalid head or base repos.')

    if pull_request['merged']:
        return jsonify(updated=False, reason='Pull request is already merged.')

    body = pull_request['body'] or ''
    if body.find(DEPLOY_MARKER) == -1:
        return jsonify(updated=False, reason='Deploy marker not found.')

    ref_sha = head['sha']
    branch = head['ref']
    if ref_sha:
        updated, reason = bump_version(branch, 'bin/bump-sentry', ref_sha)
        return jsonify(updated=updated, reason=reason)

    return jsonify(updated=False, reason='Commit not relevant for deploy sync.')


@app.route('/', methods=['POST'])
def index():
    if not IS_DEV:
        # Validate payload signature
        signature = hmac.new(GITHUB_WEBHOOK_SECRET.encode('utf-8'),
                             request.data, hashlib.sha1).hexdigest()
        if not hmac.compare_digest(signature, str(request.headers.get('X-Hub-Signature', '').replace('sha1=', ''))):
            return jsonify(updated=False, reason='Cannot validate payload signature.')

    event_type = request.headers.get('X-GitHub-Event')

    if event_type == 'push':
        return process_push()
    elif event_type == 'pull_request':
        return process_pull_request()
    else:
        return jsonify(updated=False, reason='Unsupported event type.')


if not app.debug:
    import logging
    app.logger.addHandler(logging.StreamHandler())

if not IS_DEV and not GITHUB_WEBHOOK_SECRET:
    raise SystemError('Empty GITHUB_WEBHOOK_SECRET!')
