// UI text in one place, in both languages, with a RUNTIME toggle.
//
// The whole app reads strings via `useI18n().t`, and the header has an EN/ΕΛ button that flips the
// language live (persisted in localStorage). Default is Greek. Both dictionaries stay in code, so
// nothing is lost either way.

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export type Lang = "el" | "en";
const STORAGE_KEY = "jensen_lang";

const en = {
  // Brand / app
  appName: "Jensen AI Technical Assistant",
  brandSub: "Field Service Industrial Laundry Equipment",
  loading: "Loading…",

  // Auth / header
  navChat: "Chat",
  navAdmin: "Admin",
  aiModel: "AI Model:",
  usernameLabel: "Username:",
  roleLabel: "Role:",
  signOut: "Sign out",
  changePassword: "Change password",
  roleAdmin: "admin",
  roleTechnician: "technician",

  // Login
  loginSubtitle: "Sign in to access the AI technical assistant.",
  username: "Username",
  usernamePlaceholder: "admin or technician",
  password: "Password",
  loginFailed: "Login failed",
  signingIn: "Signing in…",
  signIn: "Sign in",

  // Change password
  cpTitle: "Change password",
  cpForcedSubtitle: "Your account requires a new password before you can continue.",
  cpNormalSubtitle: "Update the password for your account.",
  cpCurrent: "Current password",
  cpNew: "New password",
  cpConfirm: "Confirm new password",
  cpMismatch: "New passwords don't match",
  cpFailed: "Could not change password",
  cpUpdated: "Password updated.",
  cpUpdating: "Updating…",
  cpUpdate: "Update password",
  cpSignOutInstead: "Sign out instead",
  cancel: "Cancel",

  // Chat / conversations
  chatsTitle: "Chats",
  showConversations: "Show conversations",
  newChat: "+ New chat",
  noConversations: "No conversations yet.",
  deleteConversation: "Delete conversation",
  timeJustNow: "just now",
  timeMin: "m",
  timeHour: "h",
  timeDay: "d",

  // Composer
  askPlaceholder: "Ask a troubleshooting question…",
  listening: "Listening… speak now",
  readingPhoto: "Reading the photo…",
  micStart: "Dictate your question",
  micStop: "Stop dictation",
  cameraAria: "Add a photo of the machine display",
  cameraTitle: "Take or choose a photo of the machine display (reads the error/code)",
  noTextFound: "No readable text found in the photo — try a closer, clearer shot.",
  couldntReadImage: "Couldn't read the image",

  // Empty state / suggestions
  emptyTitle: "How can I help with your service call?",
  // emptyDesc:
  //   "Ask a troubleshooting question. Answers come from the manuals in your library — with source citations. If it's not in the manuals, I'll say so.",
  // suggestion1: "Washer drum won't spin — where do I start?",
  // suggestion2: "What does error code E14 mean on the ironer?",
  // suggestion3: "Steam valve is leaking — safe shutdown steps?",

  // Message bubble
  avatarYou: "You",
  webBadge: "🌐 From a web search — verify before acting",

  // Admin — tabs
  tabUsers: "Users",
  tabLibrary: "Library",
  tabAudit: "Audit log",

  // Admin — users
  usersHeading: "Users & access",
  usersNote: "Mirrors Cognito: roles, instant disable (revocation), and an access-expiry date.",
  emailPlaceholder: "email",
  passwordPlaceholder: "password",
  accessExpiryTitle: "Access expiry (optional)",
  addUser: "Add user",
  searchEmail: "Search email…",
  allRoles: "All roles",
  allStatuses: "All statuses",
  statusActive: "active",
  statusDisabled: "disabled",
  colEmail: "Email",
  colRole: "Role",
  colStatus: "Status",
  colExpires: "Expires",
  mustReset: "must reset",
  disable: "Disable",
  enable: "Enable",
  resetPassword: "Reset password",
  delete: "Delete",
  resetPromptTitle: "Set a temporary password for",
  resetPromptHint: "They'll be forced to change it at next sign-in.",

  // Admin — documents
  docsHeading: "Document library",
  docsNote:
    "Upload PDF manuals — they're parsed, chunked, embedded, and searchable. The local stand-in for the S3 / Drive drop.",
  uploadIngest: "Upload & ingest",
  searchFilename: "Search filename…",
  colFile: "File",
  colChunks: "Chunks",
  colAdded: "Added",
  uploadingPrefix: "Uploading & ingesting",
  uploadingSuffix: "— this can take a minute…",
  ingestedPrefix: "Ingested",
  chunksWord: "chunks",

  // Admin — audit
  auditHeading: "Query audit log",
  auditNote: "Who asked what, and whether it was answered from the library or the web.",
  searchQuestionUser: "Search question or user…",
  allSources: "All sources",
  allUsers: "All users",
  refresh: "Refresh",
  colTime: "Time",
  colUser: "User",
  colSource: "Source",
  colQuestion: "Question",
};

export type Strings = typeof en;

const el: Strings = {
  appName: "Jensen AI Τεχνικός Βοηθός",
  brandSub: "Τεχνική Εξυπηρέτηση Πεδίου · Βιομηχανικός Εξοπλισμός Πλυντηρίων",
  loading: "Φόρτωση…",

  navChat: "Συνομιλία",
  navAdmin: "Διαχείριση",
  aiModel: "Μοντέλο AI:",
  usernameLabel: "Χρήστης:",
  roleLabel: "Ρόλος:",
  signOut: "Αποσύνδεση",
  changePassword: "Αλλαγή κωδικού",
  roleAdmin: "διαχειριστής",
  roleTechnician: "τεχνικός",

  loginSubtitle: "Συνδεθείτε για πρόσβαση στον τεχνικό βοηθό AI.",
  username: "Όνομα χρήστη",
  usernamePlaceholder: "admin ή technician",
  password: "Κωδικός πρόσβασης",
  loginFailed: "Η σύνδεση απέτυχε",
  signingIn: "Σύνδεση…",
  signIn: "Σύνδεση",

  cpTitle: "Αλλαγή κωδικού",
  cpForcedSubtitle: "Ο λογαριασμός σας απαιτεί νέο κωδικό πριν συνεχίσετε.",
  cpNormalSubtitle: "Ενημερώστε τον κωδικό του λογαριασμού σας.",
  cpCurrent: "Τρέχων κωδικός",
  cpNew: "Νέος κωδικός",
  cpConfirm: "Επιβεβαίωση νέου κωδικού",
  cpMismatch: "Οι νέοι κωδικοί δεν ταιριάζουν",
  cpFailed: "Δεν ήταν δυνατή η αλλαγή του κωδικού",
  cpUpdated: "Ο κωδικός ενημερώθηκε.",
  cpUpdating: "Ενημέρωση…",
  cpUpdate: "Ενημέρωση κωδικού",
  cpSignOutInstead: "Αποσύνδεση αντ' αυτού",
  cancel: "Άκυρο",

  chatsTitle: "Συνομιλίες",
  showConversations: "Εμφάνιση συνομιλιών",
  newChat: "+ Νέα συνομιλία",
  noConversations: "Καμία συνομιλία ακόμη.",
  deleteConversation: "Διαγραφή συνομιλίας",
  timeJustNow: "μόλις τώρα",
  timeMin: "λ",
  timeHour: "ώ",
  timeDay: "η",

  askPlaceholder: "Κάντε μια ερώτηση αντιμετώπισης προβλήματος…",
  listening: "Ακούω… μιλήστε τώρα",
  readingPhoto: "Ανάγνωση φωτογραφίας…",
  micStart: "Υπαγόρευση ερώτησης",
  micStop: "Διακοπή υπαγόρευσης",
  cameraAria: "Προσθήκη φωτογραφίας της οθόνης του μηχανήματος",
  cameraTitle: "Τραβήξτε ή επιλέξτε φωτογραφία της οθόνης του μηχανήματος (διαβάζει τον κωδικό)",
  noTextFound: "Δεν βρέθηκε ευανάγνωστο κείμενο στη φωτογραφία — δοκιμάστε πιο κοντινή, καθαρή λήψη.",
  couldntReadImage: "Δεν ήταν δυνατή η ανάγνωση της εικόνας",

  emptyTitle: "Πώς μπορώ να βοηθήσω με την κλήση σέρβις σας;",
  emptyDesc:
    "Κάντε μια ερώτηση αντιμετώπισης προβλήματος. Οι απαντήσεις προέρχονται από τα εγχειρίδια της βιβλιοθήκης σας — με παραπομπές πηγών. Αν δεν υπάρχει στα εγχειρίδια, θα σας το πω.",
  suggestion1: "Ο κάδος του πλυντηρίου δεν γυρίζει — από πού ξεκινάω;",
  suggestion2: "Τι σημαίνει ο κωδικός σφάλματος E14 στο σιδερωτήριο;",
  suggestion3: "Διαρροή από τη βαλβίδα ατμού — βήματα ασφαλούς απενεργοποίησης;",

  avatarYou: "Εσείς",
  webBadge: "🌐 Από αναζήτηση στο web — επαληθεύστε πριν ενεργήσετε",

  tabUsers: "Χρήστες",
  tabLibrary: "Βιβλιοθήκη",
  tabAudit: "Αρχείο καταγραφής",

  usersHeading: "Χρήστες & πρόσβαση",
  usersNote:
    "Αντικατοπτρίζει το Cognito: ρόλοι, άμεση απενεργοποίηση (ανάκληση) και ημερομηνία λήξης πρόσβασης.",
  emailPlaceholder: "email",
  passwordPlaceholder: "κωδικός",
  accessExpiryTitle: "Λήξη πρόσβασης (προαιρετικό)",
  addUser: "Προσθήκη χρήστη",
  searchEmail: "Αναζήτηση email…",
  allRoles: "Όλοι οι ρόλοι",
  allStatuses: "Όλες οι καταστάσεις",
  statusActive: "ενεργός",
  statusDisabled: "ανενεργός",
  colEmail: "Email",
  colRole: "Ρόλος",
  colStatus: "Κατάσταση",
  colExpires: "Λήξη",
  mustReset: "απαιτείται επαναφορά",
  disable: "Απενεργοποίηση",
  enable: "Ενεργοποίηση",
  resetPassword: "Επαναφορά κωδικού",
  delete: "Διαγραφή",
  resetPromptTitle: "Ορίστε προσωρινό κωδικό για",
  resetPromptHint: "Θα υποχρεωθεί να τον αλλάξει στην επόμενη σύνδεση.",

  docsHeading: "Βιβλιοθήκη εγγράφων",
  docsNote:
    "Ανεβάστε εγχειρίδια PDF — αναλύονται, τεμαχίζονται, ενσωματώνονται και γίνονται αναζητήσιμα. Το τοπικό υποκατάστατο του S3 / Drive.",
  uploadIngest: "Μεταφόρτωση & εισαγωγή",
  searchFilename: "Αναζήτηση ονόματος αρχείου…",
  colFile: "Αρχείο",
  colChunks: "Τμήματα",
  colAdded: "Προστέθηκε",
  uploadingPrefix: "Μεταφόρτωση & εισαγωγή",
  uploadingSuffix: "— μπορεί να πάρει ένα λεπτό…",
  ingestedPrefix: "Έγινε εισαγωγή",
  chunksWord: "τμήματα",

  auditHeading: "Αρχείο καταγραφής ερωτημάτων",
  auditNote: "Ποιος ρώτησε τι, και αν απαντήθηκε από τη βιβλιοθήκη ή το web.",
  searchQuestionUser: "Αναζήτηση ερώτησης ή χρήστη…",
  allSources: "Όλες οι πηγές",
  allUsers: "Όλοι οι χρήστες",
  refresh: "Ανανέωση",
  colTime: "Ώρα",
  colUser: "Χρήστης",
  colSource: "Πηγή",
  colQuestion: "Ερώτηση",
};

const DICTS: Record<Lang, Strings> = { en, el };

interface I18nValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  toggle: () => void;
  t: Strings;
}

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === "en" || saved === "el" ? saved : "el";
  });
  const setLang = useCallback((l: Lang) => {
    localStorage.setItem(STORAGE_KEY, l);
    setLangState(l);
  }, []);
  const toggle = useCallback(() => setLang(lang === "el" ? "en" : "el"), [lang, setLang]);
  const value = useMemo(() => ({ lang, setLang, toggle, t: DICTS[lang] }), [lang, setLang, toggle]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

/** Display a role value ("admin"/"technician") in the active language. */
export const roleLabel = (role: string, t: Strings): string =>
  role === "admin" ? t.roleAdmin : role === "technician" ? t.roleTechnician : role;
