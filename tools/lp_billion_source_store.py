"""Immutable shared source objects; each reservation keeps its exact manifest."""
import hashlib,os,tempfile
from pathlib import Path

def retain_source(source,store):
    source,store=Path(source),Path(store);data=source.read_bytes()
    sha=hashlib.sha256(data).hexdigest();store.mkdir(parents=True,exist_ok=True)
    destination=store/(sha+source.suffix)
    if destination.exists():
        if destination.is_symlink() or destination.read_bytes()!=data:
            raise ValueError('retained source object differs')
        return destination
    descriptor,name=tempfile.mkstemp(prefix='.source-',dir=store)
    temporary=Path(name)
    try:
        with os.fdopen(descriptor,'wb') as out:
            out.write(data);out.flush();os.fsync(out.fileno())
        temporary.chmod(0o444)
        try:os.link(temporary,destination)
        except FileExistsError:
            if destination.is_symlink() or destination.read_bytes()!=data:
                raise ValueError('concurrent retained source object differs')
    finally:temporary.unlink()
    return destination
