# Maintainer: Anshuman Singh <your.email@example.com>

pkgname=stcli
pkgver=1.1.1
pkgrel=1
pkgdesc="A beautiful CLI for Syncthing"
arch=('any')
url="https://github.com/anshumansingh0010/syncthing-cli" 
license=('MIT') # Update with the correct license if not MIT
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

# For publishing to AUR, you typically build from a release tarball
source=("$pkgname-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('c86899e082e72ae8044f05e90845ef5c8f235e594a92196c72172245eb4a8e10')

build() {
    # If the extracted directory has a different name, update this path
    cd "syncthing-cli-$pkgver"
    /usr/bin/python -m build --wheel --no-isolation
}

package() {
    cd "syncthing-cli-$pkgver"
    /usr/bin/python -m installer --destdir="$pkgdir" dist/*.whl
    
    # Optional: Install a license file if you have one
    # install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
