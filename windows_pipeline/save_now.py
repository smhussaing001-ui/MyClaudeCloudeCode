from resolve_env import connect
resolve, project, tl = connect()
print("SaveProject ->", resolve.GetProjectManager().SaveProject())
