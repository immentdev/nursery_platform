import { ROLES_BY_ORG_TYPE } from "./labels";

// Specchio della logica backend, usato solo per mostrare/nascondere comandi.
export const isNursery = (u) => ["ADMIN_NURSERY", "OPERATORE_NURSERY"].includes(u?.role);
export const isAdminNursery = (u) => u?.role === "ADMIN_NURSERY";
export const isProvider = (u) => ["OPERATIVO_PROVIDER", "PROFESSIONISTA_PROVIDER"].includes(u?.role);
export const isStartupUser = (u) => ["ADMIN_STARTUP", "OPERATIVO_STARTUP"].includes(u?.role);

export function canManage(actor, orgType, orgId, role) {
  if (!ROLES_BY_ORG_TYPE[orgType]?.includes(role)) return false;
  if (actor.role === "ADMIN_NURSERY") return true;
  if (actor.role === "OPERATORE_NURSERY") return orgType !== "NURSERY";
  if (actor.role === "ADMIN_STARTUP") return orgId === actor.organization_id;
  return false;
}

export const canManageUsers = (u) => isNursery(u) || u?.role === "ADMIN_STARTUP";
