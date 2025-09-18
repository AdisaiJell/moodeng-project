from controllers.role_controller import create_role,get_all_roles
from schemas import RoleCreate
from database import SessionLocal, Base

db_session = SessionLocal()
# # add new Role
# roles:RoleCreate = []
# role1 = RoleCreate(roleId=1,roleName='admin')
# role2 = RoleCreate(roleId=2,roleName='user')
# role3 = RoleCreate(roleId=3,roleName='guest')

# roles.append(role1)
# roles.append(role2)
# roles.append(role3)

# for i in roles:
#     create_role(db_session, i)
    
# get all role
roles = get_all_roles(db_session)
for role in roles:
    print(role.roleId, role.roleName)



