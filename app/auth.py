import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing access token",
                                 headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"],
                              issuer=settings.jwt_issuer, options={"require": ["exp", "iat", "sub", "iss"]})
        username = payload.get("sub")
    except jwt.InvalidTokenError:
        raise unauthorized
    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
    if user is None:
        raise unauthorized
    return user

def require_permission(permission: str):
    def dependency(user: User = Depends(current_user)) -> User:
        granted = {perm for role in user.roles for perm in role.permissions}
        if permission not in granted:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dependency

