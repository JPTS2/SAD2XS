"""
(Unofficial) SAD to XSuite Converter
"""
################################################################################
# Required Packages
################################################################################
import xtrack as xt
import matplotlib.pyplot as plt

################################################################################
# Environments
################################################################################
env_bte = xt.Environment()
env_btp = xt.Environment()
env_ler = xt.Environment()
env_her = xt.Environment()

################################################################################
# Load all lines
################################################################################

########################################
# BTE
########################################
env_bte.call("out/kek_bte.py")
env_bte.call("out/kek_bte_import_optics.py")
bte = env_bte.lines["line"]
bte.replace_all_repeated_elements()

########################################
# BTP
########################################
env_btp.call("out/kek_btp.py")
env_btp.call("out/kek_btp_import_optics.py")
btp = env_btp.lines["line"]
btp.replace_all_repeated_elements()

########################################
# LER
########################################
env_ler.call("out/ler_giulia.py")
env_ler.call("out/ler_giulia_import_optics.py")
ler = env_ler.lines["line"]
ler.replace_all_repeated_elements()

########################################
# HER
########################################
env_her.call("out/her.py")
env_her.call("out/her_import_optics.py")
her = env_her.lines["line"]
her.replace_all_repeated_elements()

################################################################################
# Survey
################################################################################

########################################
# Reference Elements
########################################
INJ_ELE     = "pinjax0"
INJ_ELE_BTE = "qi4e..1" # The offset marker is missing but the slice location is fine
BTP_ELE     = "b3p_entry.0"
BTE_ELE     = "b1e.4"

########################################
# Align BTP to LER
########################################
# Rotation
sv_ler  = ler.survey()
sv_btp  = btp.survey()
dT_btp  = sv_ler["theta", INJ_ELE] - sv_btp["theta", INJ_ELE]

# X, Y, Z translation
sv_ler  = ler.survey()
sv_btp  = btp.survey(theta0 = dT_btp)
dX_btp  = sv_ler["X", INJ_ELE] - sv_btp["X", INJ_ELE]
dY_btp  = sv_ler["Y", INJ_ELE] - sv_btp["Y", INJ_ELE]
dZ_btp  = sv_ler["Z", INJ_ELE] - sv_btp["Z", INJ_ELE]

########################################
# Align BTE to BTP
########################################
# Rotation
sv_btp  = btp.survey(X0 = dX_btp, Y0 = dY_btp, Z0 = dZ_btp, theta0 = dT_btp)
sv_bte  = bte.survey()
dT_bte  = sv_btp["theta", BTP_ELE] - sv_bte["theta", BTE_ELE]

# X, Z translation
sv_btp  = btp.survey(X0 = dX_btp, Y0 = dY_btp, Z0 = dZ_btp, theta0 = dT_btp)
sv_bte  = bte.survey(theta0 = dT_bte)
dX_bte  = sv_btp["X", BTP_ELE] - sv_bte["X", BTE_ELE]
dZ_bte  = sv_btp["Z", BTP_ELE] - sv_bte["Z", BTE_ELE]

# Y translation
sv_btp  = btp.survey(X0 = dX_btp, Y0 = dY_btp, Z0 = dZ_btp, theta0 = dT_btp)
sv_bte  = bte.survey(X0 = dX_bte, Z0 = dZ_bte, theta0 = dT_bte)
dY_bte  = sv_btp.Y[-1] - sv_bte.Y[-1]

########################################
# Align HER to BTE
########################################
# Rotation
sv_bte  = bte.survey(X0 = dX_bte, Y0 = dY_bte, Z0 = dZ_bte, theta0 = dT_bte)
sv_her  = her.survey()
dT_her  = sv_bte["theta", INJ_ELE_BTE] - sv_her["theta", INJ_ELE]

# X, Y, Z translation
sv_bte  = bte.survey(X0 = dX_bte, Y0 = dY_bte, Z0 = dZ_bte, theta0 = dT_bte)
sv_her  = her.survey(theta0 = dT_her)
dX_her  = sv_bte["X", INJ_ELE_BTE] - sv_her["X", INJ_ELE]
dY_her  = sv_bte["Y", INJ_ELE_BTE] - sv_her["Y", INJ_ELE]
dZ_her  = sv_bte["Z", INJ_ELE_BTE] - sv_her["Z", INJ_ELE]

########################################
# Final Surveys
########################################
sv_ler  = ler.survey()
sv_btp  = btp.survey(X0 = dX_btp, Y0 = dY_btp, Z0 = dZ_btp, theta0 = dT_btp)
sv_bte  = bte.survey(X0 = dX_bte, Y0 = dY_bte, Z0 = dZ_bte, theta0 = dT_bte)
sv_her  = her.survey(X0 = dX_her, Y0 = dY_her, Z0 = dZ_her, theta0 = dT_her)

########################################
# Plot in 3D BTs only
########################################
fig = plt.figure(figsize = (12, 12))
ax  = fig.add_subplot(111, projection = '3d')

ax.plot(sv_btp.Z, sv_btp.X, sv_btp.Y * 10, label = "BTP", color= "r", linewidth = 3, linestyle = "--")
ax.plot(sv_bte.Z, sv_bte.X, sv_bte.Y * 10, label = "BTE", color= "b", linewidth = 3, linestyle = "--")
ax.set_xlabel('Z [m]')
ax.set_ylabel('X [m]')
ax.set_zlabel('10Y [m]')                                                        # type: ignore
ax.set_aspect('equal')
ax.legend()

########################################
# Plot in 3D
########################################
fig = plt.figure(figsize = (12, 12))
ax  = fig.add_subplot(111, projection = '3d')

ax.plot(sv_ler.Z, sv_ler.X, sv_ler.Y, label = "LER", color= "r", linewidth = 3)
ax.plot(sv_her.Z, sv_her.X, sv_her.Y, label = "HER", color= "b", linewidth = 3)
ax.plot(sv_btp.Z, sv_btp.X, sv_btp.Y, label = "BTP", color= "r", linewidth = 3, linestyle = "--")
ax.plot(sv_bte.Z, sv_bte.X, sv_bte.Y, label = "BTE", color= "b", linewidth = 3, linestyle = "--")
ax.set_xlabel('Z [m]')
ax.set_ylabel('X [m]')
ax.set_zlabel('Y [m]')                                                          # type: ignore
ax.legend()

########################################
# Show plots
########################################
plt.show()
