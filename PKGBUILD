# Maintainer: Anshuman Singh <anshumansingh0010@gmail.com>

pkgname=stcli
pkgver=1.1.2
pkgrel=1
pkgdesc="A beautiful CLI for Syncthing"
arch=('any')
url="https://github.com/anshumansingh0010/syncthing-cli" 
license=('MIT') 
depends=(
    'python'
    'python-click'
    'python-requests'
    'python-rich'
    'python-urllib3'
)
makedepends=(
    'python-build'
    'python-installer'
    'python-wheel'
    'python-setuptools'
)

source=("$pkgname-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('9965b6d334ebbc01a1f7a0cc5e1ed2d87099664f033472ba4ff8a3e69e43f27e')

build() {
    cd "syncthing-cli-$pkgver"
    /usr/bin/python -m build --wheel --no-isolation
}

package() {
    cd "syncthing-cli-$pkgver"
    /usr/bin/python -m installer --destdir="$pkgdir" dist/*.whl
}
