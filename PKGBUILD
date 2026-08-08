# Maintainer: Anshuman Singh <anshumansingh0010@gmail.com>

pkgname=stcli
pkgver=1.1.1
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
sha256sums=('c86899e082e72ae8044f05e90845ef5c8f235e594a92196c72172245eb4a8e10')

build() {
    cd "syncthing-cli-$pkgver"
    /usr/bin/python -m build --wheel --no-isolation
}

package() {
    cd "syncthing-cli-$pkgver"
    /usr/bin/python -m installer --destdir="$pkgdir" dist/*.whl
}
