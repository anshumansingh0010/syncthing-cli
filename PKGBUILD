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
sha256sums=('52052552cf3d526762b2febab89a418edc6d50de08ef42fa040537cb4620d675')

build() {
    cd "syncthing-cli-$pkgver"
    /usr/bin/python -m build --wheel --no-isolation
}

package() {
    cd "syncthing-cli-$pkgver"
    /usr/bin/python -m installer --destdir="$pkgdir" dist/*.whl
}
