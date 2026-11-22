import React, { useCallback, useEffect, useRef, useState } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

function formatTime(value) {
  if (!value) return '';
  try { return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
  catch { return ''; }
}

function Icon({ name }) {
  const paths = {
    bot: <><rect x="4" y="7" width="16" height="13" rx="4"/><path d="M12 3v4M9 13h.01M15 13h.01M9 17h6"/><path d="M2 12h2M20 12h2"/></>,
    activity: <><path d="M3 12h4l3-8 4 16 3-8h4"/></>,
    upload: <><path d="M12 16V4m-5 5 5-5 5 5"/><path d="M4 16v4h16v-4"/></>,
    send: <><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h8"/></>,
    check: <><path d="m5 12 4 4L19 6"/></>,
    globe: <><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/></>,
    spark: <><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2Z"/><path d="m19 14 1 3 3 1-3 1-1 3-1-3-3-1 3-1Z"/></>,
    lock: <><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></>,
    user: <><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></>,
    logout: <><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></>,
    folder: <><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></>,
    eye: <><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></>,
    arrowRight: <><path d="M5 12h14M12 5l7 7-7 7"/></>,
    scan: <><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><line x1="7" y1="12" x2="17" y2="12"/></>,
    docs: <><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/><path d="M6 6h10M6 10h10M6 14h6"/></>,
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true" className="icon" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name] || paths.spark}</svg>;
}

// ============= ONBOARDING FIELD DEFINITIONS =============
const ONBOARDING_STEPS = [
  {
    id: 'personal',
    title: 'Personal Details',
    subtitle: 'Basic identity information used across applications',
    icon: 'user',
    fields: [
      { key: 'full_name', label: 'Full Name', type: 'text', required: true, placeholder: 'As per official documents' },
      { key: 'given_name', label: 'First Name', type: 'text', required: true },
      { key: 'middle_name', label: 'Middle Name', type: 'text' },
      { key: 'surname', label: 'Last Name', type: 'text', required: true },
      { key: 'date_of_birth', label: 'Date of Birth', type: 'text', required: true, placeholder: 'DD/MM/YYYY' },
      { key: 'gender', label: 'Gender', type: 'select', options: ['Male', 'Female', 'Other'], required: true },
      { key: 'nationality', label: 'Nationality', type: 'text', required: true, placeholder: 'e.g. Indian' },
      { key: 'marital_status', label: 'Marital Status', type: 'select', options: ['Single', 'Married', 'Divorced', 'Widowed'] },
      { key: 'place_of_birth', label: 'Place of Birth', type: 'text' },
      { key: 'religion', label: 'Religion', type: 'text' },
      { key: 'community', label: 'Community / Category', type: 'text' },
      { key: 'mother_tongue', label: 'Mother Tongue', type: 'text' },
      { key: 'blood_group', label: 'Blood Group', type: 'select', options: ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'] },
    ]
  },
  {
    id: 'contact',
    title: 'Contact Information',
    subtitle: 'Phone, email and emergency contacts',
    icon: 'globe',
    fields: [
      { key: 'phone', label: 'Mobile Number', type: 'tel', required: true, placeholder: '+91 XXXXXXXXXX' },
      { key: 'alternate_phone', label: 'Alternate Mobile', type: 'tel' },
      { key: 'email', label: 'Email Address', type: 'email', required: true },
      { key: 'alternate_email', label: 'Alternate Email', type: 'email' },
      { key: 'emergency_contact_name', label: 'Emergency Contact Name', type: 'text' },
      { key: 'emergency_contact_phone', label: 'Emergency Contact Number', type: 'tel' },
      { key: 'emergency_contact_relationship', label: 'Emergency Contact Relationship', type: 'text' },
    ]
  },
  {
    id: 'address',
    title: 'Address',
    subtitle: 'Current and permanent address details',
    icon: 'globe',
    fields: [
      { key: 'address_line_1', label: 'Address Line 1 / Street', type: 'text', required: true },
      { key: 'address_line_2', label: 'Address Line 2 / Area', type: 'text' },
      { key: 'city', label: 'City / Town', type: 'text', required: true },
      { key: 'district', label: 'District', type: 'text' },
      { key: 'state', label: 'State / Province', type: 'text', required: true },
      { key: 'postal_code', label: 'PIN / ZIP Code', type: 'text', required: true },
      { key: 'country', label: 'Country', type: 'text', required: true, placeholder: 'India' },
      { key: 'permanent_address', label: 'Permanent Address (if different)', type: 'text' },
    ]
  },
  {
    id: 'family',
    title: 'Family Details',
    subtitle: 'Parent and guardian information',
    icon: 'user',
    fields: [
      { key: 'father_name', label: "Father's Name", type: 'text', required: true },
      { key: 'mother_name', label: "Mother's Name", type: 'text' },
      { key: 'guardian_name', label: "Guardian's Name", type: 'text' },
      { key: 'spouse_name', label: "Spouse's Name", type: 'text' },
      { key: 'father_occupation', label: "Father's Occupation", type: 'text' },
      { key: 'annual_income', label: 'Family Annual Income', type: 'text' },
    ]
  },
  {
    id: 'identity',
    title: 'Identity Documents',
    subtitle: 'Government-issued ID numbers',
    icon: 'shield',
    fields: [
      { key: 'aadhaar_number', label: 'Aadhaar Number', type: 'text', placeholder: 'XXXX XXXX XXXX' },
      { key: 'pan_number', label: 'PAN Number', type: 'text', placeholder: 'ABCDE1234F' },
      { key: 'passport_number', label: 'Passport Number', type: 'text' },
      { key: 'voter_id', label: 'Voter ID Number', type: 'text' },
      { key: 'driving_licence', label: 'Driving Licence Number', type: 'text' },
    ]
  },
  {
    id: 'education',
    title: 'Education',
    subtitle: 'Academic qualifications and institution details',
    icon: 'file',
    fields: [
      { key: 'education_level', label: 'Highest Qualification', type: 'select', options: ['10th', '12th', 'Diploma', 'Undergraduate', 'Postgraduate', 'Doctorate', 'Other'] },
      { key: 'institution', label: 'College / University Name', type: 'text' },
      { key: 'course', label: 'Course / Degree Name', type: 'text' },
      { key: 'field_of_study', label: 'Specialization / Branch', type: 'text' },
      { key: 'graduation_year', label: 'Year of Passing', type: 'text' },
      { key: 'grade', label: 'CGPA / Percentage', type: 'text' },
      { key: 'student_id', label: 'Roll Number / Student ID', type: 'text' },
    ]
  },
  {
    id: 'employment',
    title: 'Employment & Income',
    subtitle: 'Work experience and salary details',
    icon: 'activity',
    fields: [
      { key: 'employment_status', label: 'Employment Status', type: 'select', options: ['Employed', 'Self-Employed', 'Unemployed', 'Student', 'Retired'] },
      { key: 'occupation', label: 'Occupation / Job Title', type: 'text' },
      { key: 'employer', label: 'Employer / Company Name', type: 'text' },
      { key: 'years_experience', label: 'Total Work Experience', type: 'text' },
      { key: 'current_salary', label: 'Current Salary (Annual)', type: 'text' },
      { key: 'skills', label: 'Key Skills', type: 'text', placeholder: 'Comma separated' },
    ]
  },
  {
    id: 'bank',
    title: 'Bank Details',
    subtitle: 'Account information for direct benefit transfers',
    icon: 'shield',
    fields: [
      { key: 'bank_name', label: 'Bank Name', type: 'text' },
      { key: 'bank_branch', label: 'Branch Name', type: 'text' },
      { key: 'bank_account_number', label: 'Account Number', type: 'text' },
      { key: 'bank_ifsc', label: 'IFSC Code', type: 'text' },
      { key: 'bank_account_holder', label: 'Account Holder Name', type: 'text' },
    ]
  },
];


function PortalScreenshot({ workflowId, token }) {
  const [imageUrl, setImageUrl] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    let timer;

    async function refresh() {
      try {
        const response = await fetch(`${API}/api/workflows/${workflowId}/screenshot`, {
          headers: { Authorization: `Bearer ${token}` },
          signal,
        });
        const image = response.ok ? await response.blob() : null;
        if (!signal.aborted) setImageUrl(image ? URL.createObjectURL(image) : '');
      } catch {
        if (!signal.aborted) setImageUrl('');
      } finally {
        if (!signal.aborted) timer = setTimeout(refresh, 2500);
      }
    }

    refresh();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [workflowId, token]);

  useEffect(() => () => {
    if (imageUrl) URL.revokeObjectURL(imageUrl);
  }, [imageUrl]);

  if (!imageUrl) return null;
  return <div className="portal-screenshot-wrap"><img src={imageUrl} alt="Live portal" className="portal-screenshot" /></div>;
}

function PasswordPrompt({ question, busy, onAnswer }) {
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  return (
    <form className="credentials-box" onSubmit={event => {
      event.preventDefault();
      if (!busy && password) onAnswer(question.id, password, remember);
    }}>
      <div className="credentials-title">
        <Icon name="lock" />
        <div><b>{question.label}</b><small>{question.portal}</small></div>
      </div>
      <div className="credentials-form">
        <div className="credentials-row">
          <input className="credentials-input" aria-label={question.label} placeholder="Portal password"
            type="password" autoComplete="off" value={password} onChange={event => setPassword(event.target.value)}
            maxLength={512} disabled={busy} required />
          <button className="credentials-submit" disabled={busy || !password}>Fill password</button>
        </div>
        {question.remember && (
          <label className="credentials-alt">
            <input type="checkbox" checked={remember} onChange={event => setRemember(event.target.checked)} disabled={busy} />
            {' '}Remember this password for this portal
          </label>
        )}
      </div>
    </form>
  );
}

export default function App() {
  const [session, setSession] = useState(() => ({ token: localStorage.getItem('orq_token') || '', user: null }));
  const updateSession = useCallback((token, user = null) => {
    if (token) localStorage.setItem('orq_token', token);
    else localStorage.removeItem('orq_token');
    setSession({ token, user });
  }, []);

  return <Workspace key={session.token} token={session.token} initialUser={session.user} updateSession={updateSession} />;
}

function Workspace({ token, initialUser, updateSession }) {
  // Auth state
  const [currentUser, setCurrentUser] = useState(initialUser);
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'register'
  const [authEmail, setAuthEmail] = useState('');
  const [authPass, setAuthPass] = useState('');
  const [authName, setAuthName] = useState('');
  const [authError, setAuthError] = useState('');
  const [authBusy, setAuthBusy] = useState(false);
  const [showAuthPass, setShowAuthPass] = useState(false);

  // Onboarding state
  const [onboardingPhase, setOnboardingPhase] = useState('upload'); // 'upload' (Step 0: Document Upload) or 'wizard' (Form Review)
  const [onboardingStep, setOnboardingStep] = useState(0);
  const [onboardingData, setOnboardingData] = useState(() => initialUser ? { full_name: initialUser.full_name, email: initialUser.email } : {});
  const [onboardingSaving, setOnboardingSaving] = useState(false);
  const [uploadedDocs, setUploadedDocs] = useState([]);
  const [docUploading, setDocUploading] = useState(false);
  const [docSuccessMsg, setDocSuccessMsg] = useState('');

  // Main app state
  const [page, setPage] = useState('chat'); // 'chat', 'vault', 'profile'
  const [workflow, setWorkflow] = useState(null);
  const [messages, setMessages] = useState([]);
  const [events, setEvents] = useState([]);
  const [recent, setRecent] = useState([]);
  const [text, setText] = useState('');
  const [otp, setOtp] = useState('');
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [attached, setAttached] = useState([]);
  const [userDocs, setUserDocs] = useState([]);
  const [userProfile, setUserProfile] = useState({});

  const messagesEnd = useRef(null);
  const fileRef = useRef(null);
  const vaultFileRef = useRef(null);
  const onboardingFileRef = useRef(null);
  const wizardFileRef = useRef(null);

  const authHeaders = useCallback(() => token ? { 'Authorization': `Bearer ${token}` } : {}, [token]);

  const request = useCallback(async (path, options = {}) => {
    const headers = { ...authHeaders(), ...(options.headers || {}) };
    const response = await fetch(`${API}${path}`, { ...options, headers });
    let payload = {};
    try { payload = await response.json(); } catch { /* non-JSON */ }
    if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
    return payload;
  }, [authHeaders]);

  // ============= AUTH =============
  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    request('/api/auth/me', { signal: controller.signal }).then(u => {
      if (controller.signal.aborted) return;
      setCurrentUser(u);
      setOnboardingData(prev => ({ full_name: u.full_name, email: u.email, ...prev }));
    }).catch(() => {
      if (!controller.signal.aborted) updateSession('');
    });
    return () => controller.abort();
  }, [token, request, updateSession]);

  async function handleAuth(e) {
    e.preventDefault(); setAuthBusy(true); setAuthError('');
    try {
      if (authMode === 'register') {
        const res = await request('/api/auth/register', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: authEmail, password: authPass, full_name: authName }),
        });
        updateSession(res.token, res.user);
      } else {
        const res = await request('/api/auth/login', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: authEmail, password: authPass }),
        });
        updateSession(res.token, res.user);
      }
    } catch (err) { setAuthError(err.message); }
    finally { setAuthBusy(false); }
  }

  function logout() {
    updateSession('');
  }

  // Pre-load user profile if in onboarding
  useEffect(() => {
    if (currentUser && !currentUser.onboarding_complete) {
      request('/api/profile').then(p => {
        if (p && Object.keys(p).length > 0) {
          setOnboardingData(prev => ({ ...p, ...prev }));
        }
      }).catch(() => {});
      request('/api/user/documents').then(docs => {
        if (docs && docs.length > 0) {
          setUploadedDocs(docs);
        }
      }).catch(() => {});
    }
  }, [currentUser, request]);

  // ============= ONBOARDING DOCUMENT UPLOAD =============
  async function handleOnboardingDocUpload(e) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setDocUploading(true);
    setError('');
    setDocSuccessMsg('');
    try {
      const form = new FormData();
      for (const f of files) {
        form.append('files', f);
      }
      const res = await request('/api/user/documents/batch', {
        method: 'POST',
        body: form,
      });

      // res.documents: list of processed docs
      setUploadedDocs(prev => [...prev, ...res.documents]);
      if (res.updated_profile) {
        setOnboardingData(prev => ({ ...prev, ...res.updated_profile }));
      }
      setDocSuccessMsg(`🎉 Successfully scanned ${res.uploaded_count} document(s) and auto-extracted ${res.total_fields_extracted} profile fields!`);
      if (onboardingFileRef.current) onboardingFileRef.current.value = '';
      if (wizardFileRef.current) wizardFileRef.current.value = '';
    } catch (err) {
      setError(err.message);
    } finally {
      setDocUploading(false);
    }
  }

  // ============= ONBOARDING FORM WIZARD =============
  function handleOnboardingField(key, value) {
    setOnboardingData(prev => ({ ...prev, [key]: value }));
  }

  async function saveOnboardingStep(stepIndex) {
    const step = ONBOARDING_STEPS[stepIndex];
    const fields = {};
    for (const f of step.fields) {
      if (onboardingData[f.key]) fields[f.key] = onboardingData[f.key];
    }
    if (Object.keys(fields).length === 0) return;
    setOnboardingSaving(true);
    try {
      await request('/api/profile/onboarding', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fields, category: step.id }),
      });
    } catch { /* continue */ }
    finally { setOnboardingSaving(false); }
  }

  async function completeOnboarding() {
    setOnboardingSaving(true);
    try {
      if (onboardingPhase === 'wizard') {
        await saveOnboardingStep(onboardingStep);
      }
      await request('/api/profile/complete-onboarding', { method: 'POST' });
      setCurrentUser(prev => prev ? { ...prev, onboarding_complete: true } : prev);
    } catch (err) { setError(err.message); }
    finally { setOnboardingSaving(false); }
  }

  async function nextOnboardingStep() {
    await saveOnboardingStep(onboardingStep);
    if (onboardingStep < ONBOARDING_STEPS.length - 1) {
      setOnboardingStep(onboardingStep + 1);
    } else {
      await completeOnboarding();
    }
  }

  // ============= MAIN APP =============
  const refresh = useCallback(async (id = workflow?.id) => {
    try {
      const list = await request('/api/workflows');
      setRecent(list);
      if (!id) return;
      const [wf, msgs, act] = await Promise.all([
        request(`/api/workflows/${id}`),
        request(`/api/workflows/${id}/messages`),
        request(`/api/workflows/${id}/activity`),
      ]);
      setWorkflow(wf); setMessages(msgs); setEvents(act);
    } catch (err) { setError(err.message); }
  }, [request, workflow?.id]);

  const loadVault = useCallback(async () => {
    try {
      const [docs, profile] = await Promise.all([
        request('/api/user/documents'),
        request('/api/profile'),
      ]);
      setUserDocs(docs); setUserProfile(profile);
    } catch {}
  }, [request]);

  useEffect(() => {
    if (!currentUser || !currentUser.onboarding_complete) return;
    refresh();
    const timer = setInterval(() => { if (workflow?.id) refresh(workflow.id); else refresh(); }, 2500);
    return () => clearInterval(timer);
  }, [refresh, workflow?.id, currentUser]);

  useEffect(() => {
    if (page === 'vault' || page === 'profile') loadVault();
  }, [page, loadVault]);

  useEffect(() => { messagesEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages]);

  async function sendMessage(event, reply = text) {
    event?.preventDefault();
    const message = reply.trim();
    if (!message || busy) return;
    setBusy(true); setError(''); setText('');
    try {
      const result = await request('/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, workflow_id: workflow?.id || null, reply_to: workflow?.pending_input?.id || null }),
      });
      setWorkflow(result.workflow);
      await refresh(result.workflow.id);
    } catch (err) { setError(err.message); setText(message); }
    finally { setBusy(false); }
  }

  async function uploadDocument() {
    if (!file || !workflow) return;
    const form = new FormData(); form.append('file', file);
    setUploading(true); setError('');
    try {
      await request(`/api/workflows/${workflow.id}/documents`, { method: 'POST', body: form });
      setAttached(items => [...items, file.name]); setFile(null);
      if (fileRef.current) fileRef.current.value = '';
      await refresh(workflow.id);
    } catch (err) { setError(err.message); }
    finally { setUploading(false); }
  }

  async function uploadVaultDoc(e) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true); setError('');
    try {
      const form = new FormData();
      for (const f of files) form.append('files', f);
      await request('/api/user/documents/batch', { method: 'POST', body: form });
      if (vaultFileRef.current) vaultFileRef.current.value = '';
      await loadVault();
    } catch (err) { setError(err.message); }
    finally { setUploading(false); }
  }

  async function sendOtp(event) {
    event.preventDefault();
    if (!otp.trim() || !workflow) return;
    setBusy(true); setError('');
    try {
      await request(`/api/workflows/${workflow.id}/otp`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ otp: otp.trim() }),
      });
      setOtp(''); await refresh(workflow.id);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  async function sendPassword(questionId, password, remember) {
    if (!password || !workflow || busy) return;
    setBusy(true); setError('');
    try {
      const result = await request(`/api/workflows/${workflow.id}/password`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_id: questionId, password, remember }),
      });
      setWorkflow(result.workflow);
      await refresh(workflow.id);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  async function sendActionChoice(action) {
    if (!workflow) return;
    setBusy(true); setError('');
    try {
      await request(`/api/workflows/${workflow.id}/action`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      await refresh(workflow.id);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  async function sendApproval(approved) {
    if (!workflow) return;
    setBusy(true); setError('');
    try {
      await request(`/api/workflows/${workflow.id}/approve`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved }),
      });
      await refresh(workflow.id);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  async function selectWorkflow(id) { setError(''); setPage('chat'); await refresh(id); }
  function newTask() { setWorkflow(null); setMessages([]); setEvents([]); setText(''); setError(''); setOtp(''); setAttached([]); setPage('chat'); }

  const pending = workflow?.pending_input || null;
  const chatUsesDedicatedControl = ['password', 'otp', 'credentials', 'login_ready', 'manual_verification', 'submit_registration'].includes(pending?.kind);
  const progressSteps = workflow?.plan || [];
  const doneCount = progressSteps.filter(s => s.status === 'completed').length;
  const currentState = workflow?.status || 'idle';
  const isActive = ['running', 'discovering_portal', 'opening_portal'].includes(currentState);

  // ============= AUTH SCREEN =============
  if (!currentUser) {
    return (
      <div className="app-shell">
        <header className="topbar">
          <div className="brand-wrap">
            <div className="brand-mark"><Icon name="spark" /></div>
            <div><div className="brand-name">Orqentra</div><div className="brand-sub">AUTONOMOUS APPLICATION AGENT</div></div>
          </div>
        </header>
        <div className="auth-page">
          <div className="auth-card">
            <div className="auth-header">
              <div className="welcome-orb"><Icon name="spark" /></div>
              <h2>{authMode === 'register' ? 'Create your account' : 'Welcome back'}</h2>
              <p>{authMode === 'register' ? 'Register to securely store your data and automate any digital application.' : 'Log in to access your saved profile and start applying.'}</p>
            </div>
            <form onSubmit={handleAuth} className="auth-form">
              {authMode === 'register' && (
                <div className="auth-field">
                  <label>Full Name</label>
                  <input value={authName} onChange={e => setAuthName(e.target.value)} placeholder="Your full legal name" autoComplete="name" required />
                </div>
              )}
              <div className="auth-field">
                <label>Email Address</label>
                <input type="email" value={authEmail} onChange={e => setAuthEmail(e.target.value)} placeholder="name@example.com" required autoComplete="email" />
              </div>
              <div className="auth-field">
                <label>Password</label>
                <div className="auth-pass-wrap">
                  <input type={showAuthPass ? 'text' : 'password'} value={authPass} onChange={e => setAuthPass(e.target.value)} placeholder={authMode === 'register' ? 'Min 6 characters' : 'Enter password'} required autoComplete={authMode === 'register' ? 'new-password' : 'current-password'} />
                  <button type="button" className="auth-pass-toggle" onClick={() => setShowAuthPass(!showAuthPass)}>{showAuthPass ? 'Hide' : 'Show'}</button>
                </div>
              </div>
              {authError && <div className="auth-error">{authError}</div>}
              <button type="submit" className="auth-submit" disabled={authBusy}>{authBusy ? 'Please wait…' : (authMode === 'register' ? 'Register & Continue' : 'Log In')}</button>
            </form>
            <div className="auth-switch">
              {authMode === 'login' ? (
                <span>New to Orqentra? <button onClick={() => { setAuthMode('register'); setAuthError(''); }}>Create an account</button></span>
              ) : (
                <span>Already have an account? <button onClick={() => { setAuthMode('login'); setAuthError(''); }}>Log In</button></span>
              )}
            </div>
          </div>
        </div>
        <footer><span>ORQENTRA 3.1</span><span>Encrypted · Document Intelligence · Human-in-the-loop</span></footer>
      </div>
    );
  }

  // ============= ONBOARDING WIZARD =============
  if (!currentUser.onboarding_complete) {
    const extractedCount = Object.keys(onboardingData).length;

    // PHASE 1: Document Upload Step (Step 0)
    if (onboardingPhase === 'upload') {
      return (
        <div className="app-shell">
          <header className="topbar">
            <div className="brand-wrap">
              <div className="brand-mark"><Icon name="spark" /></div>
              <div><div className="brand-name">Orqentra</div><div className="brand-sub">SMART ONBOARDING · STEP 1 OF 2</div></div>
            </div>
            <div className="topbar-right">
              <button className="skip-btn" onClick={() => setOnboardingPhase('wizard')}>Skip Upload & Fill Manually →</button>
            </div>
          </header>

          <div className="doc-onboarding-page">
            <div className="doc-onboarding-hero">
              <div className="doc-onboarding-icon"><Icon name="scan" /></div>
              <h2>Submit Your Documents to Auto-Fill Registration</h2>
              <p>
                Upload any identity or educational documents you have (such as <b>Aadhaar Card, Voter ID, PAN Card, Passport, Driving Licence, Degree Certificates, Salary Slips, or Resume</b>).
                <br />
                <span className="doc-optional-badge">Optional</span> <b>You can upload any number of documents (n number).</b> Orqentra's Document Intelligence Agent will automatically extract your details, store them encrypted forever, and auto-complete your profile so you don't have to type them manually!
              </p>
            </div>

            <div className="doc-upload-box" onClick={() => onboardingFileRef.current?.click()}>
              <input
                ref={onboardingFileRef}
                type="file"
                multiple
                accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.docx"
                onChange={handleOnboardingDocUpload}
                style={{ display: 'none' }}
              />
              <div className="upload-drop-inner">
                <div className="upload-cloud-icon"><Icon name="upload" /></div>
                <b>{docUploading ? 'Scanning and extracting details from documents…' : 'Click to select or drag & drop N documents here'}</b>
                <span>Supports PDF, Word (DOCX), Images (PNG, JPG, WEBP), and Text files. Select single or multiple files.</span>
                {docUploading && <div className="mini-spinner-wrap"><span className="mini-spinner"/> <span>Analyzing documents with OCR & NLP…</span></div>}
              </div>
            </div>

            {error && <div className="error-banner"><span>{error}</span><button onClick={() => setError('')}>×</button></div>}
            {docSuccessMsg && <div className="success-banner">{docSuccessMsg}</div>}

            {/* List of uploaded documents and extracted intelligence */}
            <div className="uploaded-docs-section">
              <div className="docs-section-heading">
                <h3><Icon name="docs" /> Uploaded Documents ({uploadedDocs.length})</h3>
                <span className="extracted-counter-badge">{extractedCount} profile fields extracted</span>
              </div>

              {uploadedDocs.length === 0 ? (
                <div className="no-docs-hint">
                  <p>You haven't uploaded any documents yet. Examples of documents you can submit:</p>
                  <div className="example-pills">
                    <span>📄 Aadhaar Card</span>
                    <span>💳 PAN Card</span>
                    <span>🗳️ Voter ID Card</span>
                    <span>🛂 Passport</span>
                    <span>🚗 Driving Licence</span>
                    <span>🎓 Degree Certificate</span>
                    <span>📊 Mark Sheet</span>
                    <span>💼 Resume / CV</span>
                    <span>💰 Salary Slip</span>
                  </div>
                  <small>It is completely optional. If you prefer to enter details manually, you can skip below.</small>
                </div>
              ) : (
                <div className="docs-result-grid">
                  {uploadedDocs.map((doc, idx) => {
                    const fields = doc.extracted_fields || {};
                    const fieldCount = Object.keys(fields).length;
                    return (
                      <div className="doc-result-card" key={doc.id || idx}>
                        <div className="doc-card-top">
                          <div className="doc-card-type"><Icon name="file" /> <b>{doc.doc_type || 'Document'}</b></div>
                          <span className="doc-filename">{doc.filename || doc.doc_name}</span>
                        </div>
                        <div className="doc-card-body">
                          <span className="extracted-tag"><Icon name="check" /> {fieldCount > 0 ? `${fieldCount} fields extracted` : 'Document stored securely'}</span>
                          {fieldCount > 0 && (
                            <div className="extracted-pills">
                              {Object.entries(fields).slice(0, 8).map(([k, v]) => (
                                <span className="field-pill" key={k}>
                                  <b>{k.replace(/_/g, ' ')}:</b> {String(v).slice(0, 24)}
                                </span>
                              ))}
                              {Object.keys(fields).length > 8 && <span className="field-pill more">+{Object.keys(fields).length - 8} more</span>}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Bottom Actions */}
            <div className="doc-onboarding-actions">
              <button
                type="button"
                className="btn-add-more-docs"
                onClick={() => onboardingFileRef.current?.click()}
                disabled={docUploading}
              >
                <Icon name="plus" /> Add More Documents
              </button>

              <div className="actions-right">
                <button
                  type="button"
                  className="btn-skip-upload"
                  onClick={() => setOnboardingPhase('wizard')}
                >
                  {uploadedDocs.length > 0 ? 'Skip Remaining' : 'Fill Manually Without Upload'}
                </button>
                <button
                  type="button"
                  className="btn-proceed-wizard"
                  onClick={() => setOnboardingPhase('wizard')}
                  disabled={docUploading}
                >
                  {uploadedDocs.length > 0 ? 'Review & Complete Profile →' : 'Next Step →'}
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    // PHASE 2: Wizard to review and fill remaining fields
    const step = ONBOARDING_STEPS[onboardingStep];
    const isLastStep = onboardingStep === ONBOARDING_STEPS.length - 1;
    return (
      <div className="app-shell">
        <header className="topbar">
          <div className="brand-wrap">
            <div className="brand-mark"><Icon name="spark" /></div>
            <div><div className="brand-name">Orqentra</div><div className="brand-sub">PROFILE REVIEW & SETUP</div></div>
          </div>
          <div className="topbar-right">
            <button className="upload-quick-btn" onClick={() => wizardFileRef.current?.click()} disabled={docUploading}>
              <Icon name="upload" /> Upload document to auto-fill
            </button>
            <input
              ref={wizardFileRef}
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.docx"
              onChange={handleOnboardingDocUpload}
              style={{ display: 'none' }}
            />
            <span className="onboarding-progress">Step {onboardingStep + 1} of {ONBOARDING_STEPS.length}</span>
            <button className="skip-btn" onClick={completeOnboarding} disabled={onboardingSaving}>Finish & Launch →</button>
          </div>
        </header>

        {docSuccessMsg && <div className="success-banner" style={{ margin: '10px 34px 0' }}>{docSuccessMsg}</div>}
        {error && <div className="error-banner" style={{ margin: '10px 34px 0' }}><span>{error}</span><button onClick={() => setError('')}>×</button></div>}

        <div className="onboarding-page">
          <div className="onboarding-sidebar">
            <button
              className="onboarding-nav-item back-to-docs"
              onClick={() => setOnboardingPhase('upload')}
            >
              <span className="onboarding-nav-marker"><Icon name="scan" /></span>
              <span>Documents ({uploadedDocs.length})</span>
            </button>
            <div className="sidebar-divider" />
            {ONBOARDING_STEPS.map((s, i) => {
              const filledInStep = s.fields.filter(f => onboardingData[f.key]).length;
              return (
                <button
                  key={s.id}
                  className={`onboarding-nav-item ${i === onboardingStep ? 'active' : ''} ${i < onboardingStep ? 'done' : ''}`}
                  onClick={async () => { await saveOnboardingStep(onboardingStep); setOnboardingStep(i); }}
                >
                  <span className="onboarding-nav-marker">{i < onboardingStep ? <Icon name="check" /> : i + 1}</span>
                  <div className="nav-copy">
                    <span>{s.title}</span>
                    {filledInStep > 0 && <small>{filledInStep} filled</small>}
                  </div>
                </button>
              );
            })}
          </div>

          <div className="onboarding-main">
            <div className="onboarding-step-header">
              <div className="onboarding-step-icon"><Icon name={step.icon} /></div>
              <div>
                <h2>{step.title}</h2>
                <p>{step.subtitle} — Fields auto-filled from your documents can be edited, and remaining fields can be filled now.</p>
              </div>
            </div>

            <div className="onboarding-fields">
              {step.fields.map(f => {
                const isAutoFilled = Boolean(onboardingData[f.key]);
                return (
                  <div className={`onboarding-field ${f.required ? 'required' : ''} ${isAutoFilled ? 'has-value' : ''}`} key={f.key}>
                    <label>
                      {f.label}{f.required && <span className="req-star">*</span>}
                      {isAutoFilled && <span className="auto-filled-pill">Auto-filled</span>}
                    </label>
                    {f.type === 'select' ? (
                      <select value={onboardingData[f.key] || ''} onChange={e => handleOnboardingField(f.key, e.target.value)}>
                        <option value="">Select…</option>
                        {f.options.map(o => <option key={o} value={o}>{o}</option>)}
                      </select>
                    ) : (
                      <input
                        type={f.type || 'text'}
                        value={onboardingData[f.key] || ''}
                        onChange={e => handleOnboardingField(f.key, e.target.value)}
                        placeholder={f.placeholder || ''}
                      />
                    )}
                  </div>
                );
              })}
            </div>

            <div className="onboarding-actions">
              {onboardingStep > 0 ? (
                <button className="onboarding-back" onClick={async () => { await saveOnboardingStep(onboardingStep); setOnboardingStep(onboardingStep - 1); }}>← Back</button>
              ) : (
                <button className="onboarding-back" onClick={() => setOnboardingPhase('upload')}>← Back to Documents</button>
              )}
              <button className="onboarding-next" onClick={nextOnboardingStep} disabled={onboardingSaving}>
                {onboardingSaving ? 'Saving…' : isLastStep ? 'Complete Registration & Launch Assistant →' : 'Save & Continue →'}
              </button>
            </div>
            <p className="onboarding-note"><Icon name="shield" /> All data is encrypted with AES-Fernet and stored permanently in your local vault. Only mandatory fields (*) are essential.</p>
          </div>
        </div>
      </div>
    );
  }

  // ============= MAIN WORKSPACE APPLICATION =============
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-wrap">
          <div className="brand-mark"><Icon name="spark" /></div>
          <div><div className="brand-name">Orqentra</div><div className="brand-sub">AUTONOMOUS APPLICATION AGENT</div></div>
        </div>
        <div className="topbar-right">
          <nav className="main-nav">
            <button className={`nav-btn ${page === 'chat' ? 'active' : ''}`} onClick={() => setPage('chat')}><Icon name="bot" /> Assistant</button>
            <button className={`nav-btn ${page === 'vault' ? 'active' : ''}`} onClick={() => setPage('vault')}><Icon name="folder" /> Vault ({userDocs.length})</button>
            <button className={`nav-btn ${page === 'profile' ? 'active' : ''}`} onClick={() => setPage('profile')}><Icon name="user" /> Profile</button>
          </nav>
          <div className="user-pill"><Icon name="user" /><span>{currentUser.full_name || currentUser.email}</span></div>
          <button className="logout-btn" onClick={logout} title="Log out"><Icon name="logout" /></button>
          {page === 'chat' && <button className="new-task" onClick={newTask}><Icon name="plus" /> New task</button>}
        </div>
      </header>

      {page === 'vault' && (
        <div className="vault-page">
          <div className="vault-header">
            <h2><Icon name="folder" /> Permanent Document Vault</h2>
            <p>Your documents are permanently stored on this machine and encrypted at rest. Upload single or multiple documents (Aadhaar, Voter ID, PAN, Certificates, Resume) — Orqentra will extract details to auto-fill future applications.</p>
          </div>
          <div className="vault-upload-area" onClick={() => vaultFileRef.current?.click()}>
            <input ref={vaultFileRef} type="file" multiple accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp" onChange={uploadVaultDoc} style={{ display: 'none' }} />
            <Icon name="upload" />
            <div>
              <b>{uploading ? 'Scanning and storing documents…' : 'Click to upload N documents to your vault'}</b>
              <small>Supports multiple PDF, DOCX, PNG, JPG, WEBP. Extracted facts are automatically added to your profile.</small>
            </div>
          </div>
          {error && <div className="error-banner"><span>{error}</span><button onClick={() => setError('')}>×</button></div>}
          <div className="vault-grid">
            {userDocs.length === 0 && <p className="empty-caption">No documents yet. Click above to upload identity proofs, certificates, or resumes.</p>}
            {userDocs.map(doc => (
              <div className="vault-doc-card" key={doc.id}>
                <div className="vault-doc-icon"><Icon name="file" /></div>
                <div className="vault-doc-info">
                  <b>{doc.doc_name}</b>
                  <small>{doc.doc_type} · {formatTime(doc.created_at)}</small>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {page === 'profile' && (
        <div className="vault-page">
          <div className="vault-header">
            <h2><Icon name="user" /> Your Applicant Profile</h2>
            <p>All stored details encrypted per-user. The agent pulls from this profile to automatically fill online portals.</p>
          </div>
          {error && <div className="error-banner"><span>{error}</span><button onClick={() => setError('')}>×</button></div>}
          <div className="profile-grid">
            {Object.keys(userProfile).length === 0 && <p className="empty-caption">No profile data yet. Upload documents or complete onboarding to populate your profile.</p>}
            {Object.entries(userProfile).map(([key, val]) => (
              <div className="profile-field-card" key={key}>
                <span className="profile-key">{key.replace(/_/g, ' ')}</span>
                <span className="profile-val">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {page === 'chat' && (
        <div className="workspace">
          <section className="chat-panel">
            <div className="panel-heading">
              <div className="panel-title"><span className="heading-icon chat-icon"><Icon name="bot" /></span><div><h1>Assistant</h1><p>Describe what you want to apply for. I'll handle the work.</p></div></div>
              {workflow && <span className={`state-pill ${currentState}`}>{currentState.replaceAll('_', ' ')}</span>}
            </div>

            {!workflow ? (
              <div className="welcome-state">
                <div className="welcome-orb"><Icon name="spark" /></div>
                <h2>What would you like to apply for?</h2>
                <p>Tell me what you need. I'll find the official portal, use your stored encrypted profile and documents, and fill the application in the background.</p>
                <div className="prompt-suggestions">
                  {[
                    'Apply for a government scholarship using my existing documents.',
                    'Find and complete the official passport renewal application.',
                    'Apply for a job using my saved resume and profile.',
                    'Apply for a new driving license online.',
                  ].map((example, i) => <button key={i} className="suggestion" onClick={() => setText(example)}>{example}<span>↗</span></button>)}
                </div>
              </div>
            ) : (
              <div className="conversation">
                {messages.map((message, i) => (
                  <div className={`message-row ${message.role}`} key={`${i}-${message.created_at}`}>
                    {message.role === 'assistant' && <div className="message-avatar"><Icon name="bot" /></div>}
                    <div className={`message-bubble ${message.kind || ''}`}>
                      {message.content.split(/\n/).map((line, li) => {
                        const urlMatch = line.match(/^\s*(\d+\.\s*)?\[([^\]]+)\]\((https:\/\/[^)]+)\)(.*)$/);
                        if (urlMatch) return <div className="portal-inline" key={li}><a href={urlMatch[3]} target="_blank" rel="noreferrer">{urlMatch[2]}</a><span>{urlMatch[4]}</span></div>;
                        return <p key={li}>{message.role === 'assistant'
                          ? (line || '\u00a0').split(/(\*\*[^*]+\*\*)/).map((part, index) =>
                            index % 2 ? <strong key={index}>{part.slice(2, -2)}</strong> : part)
                          : line || '\u00a0'}</p>;
                      })}
                      <time>{formatTime(message.created_at)}</time>
                    </div>
                    {message.role === 'user' && <div className="user-avatar">You</div>}
                  </div>
                ))}
                {isActive && <div className="typing-row"><div className="message-avatar"><Icon name="bot" /></div><div className="typing-bubble"><i/><i/><i/><span>Working in the background…</span></div></div>}
                <div ref={messagesEnd} />
              </div>
            )}

            {error && <div className="error-banner"><span>{error}</span><button onClick={() => setError('')}>×</button></div>}

            {pending?.kind === 'portal_confirmation' && workflow?.portal_candidates?.length > 0 && (
              <div className="portal-choice">
                <div className="choice-title"><Icon name="globe" /> Possible application portal</div>
                {workflow.portal_candidates.slice(0, 3).map((candidate, i) => <div className="candidate" key={candidate.url}>
                  <div><b>{candidate.title}</b><a href={candidate.url} target="_blank" rel="noreferrer">{candidate.host || candidate.url}</a><small>Match confidence: {Math.round((candidate.confidence || 0) * 100)}%</small></div>
                  <button onClick={() => { setBusy(true); request(`/api/workflows/${workflow.id}/portal`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: candidate.url }) }).then(() => refresh(workflow.id)).catch(e => setError(e.message)).finally(() => setBusy(false)); }} disabled={busy}>{i === 0 ? 'Use portal' : 'Select'}</button>
                </div>)}
              </div>
            )}

            {pending?.kind === 'portal_action_choice' && pending?.choices?.length > 0 && (
              <div className="action-choice-box">
                <div className="action-choice-title"><Icon name="globe"/> Choose how to proceed on the portal:</div>
                <div className="action-buttons">
                  {pending.choices.map((choice, i) => (
                    <button key={i} className="action-btn" disabled={busy} onClick={() => sendActionChoice(choice.action)}>{choice.label}</button>
                  ))}
                </div>
              </div>
            )}

            {pending?.kind === 'password' && (
              <PasswordPrompt key={pending.id} question={pending} busy={busy} onAnswer={sendPassword} />
            )}

            {['credentials', 'login_ready', 'manual_verification', 'submit_registration'].includes(pending?.kind) && (
              <div className="option-chips">
                <button type="button" className="action-btn" disabled={busy}
                  onClick={event => sendMessage(event, pending.kind === 'submit_registration' ? 'submit registration' : 'ready')}>
                  {pending.kind === 'submit_registration' ? 'Submit registration' : 'Continue in chat'}
                </button>
              </div>
            )}

            {pending?.kind === 'approval' && (
              <div className="approval-box">
                <div className="approval-title"><Icon name="check" /><div><b>Portal Option Approval</b><small>Please confirm whether to proceed.</small></div></div>
                <div className="approval-actions">
                  <button className="approval-btn" onClick={() => sendApproval(true)} disabled={busy}>Approve & Continue</button>
                  <button className="reject-btn" onClick={() => sendApproval(false)} disabled={busy}>Change Option</button>
                </div>
              </div>
            )}

            {pending?.kind === 'otp' && (
              <form className="otp-box" onSubmit={sendOtp}>
                <div className="otp-title"><Icon name="shield" /><div><b>Verification code requested</b><small>Enter the OTP. It is sent directly to the browser and not saved.</small></div></div>
                <div className="otp-entry"><input value={otp} onChange={e => setOtp(e.target.value.replace(/\D/g, '').slice(0, 12))} inputMode="numeric" autoComplete="one-time-code" placeholder="Enter OTP" /><button disabled={busy || otp.length < 4}>Send OTP</button></div>
              </form>
            )}

            {pending?.kind === 'detail' && pending?.options?.length > 0 && (
              <div className="option-chips">
                <span className="chips-label">Available options:</span>
                {pending.options.length > 8 ? (
                  <select aria-label={pending.label} value="" disabled={busy} onChange={event => sendMessage(event, event.target.value)}>
                    <option value="" disabled>Choose an option</option>
                    {pending.options.map((option, index) => <option key={index} value={option}>{option}</option>)}
                  </select>
                ) : pending.options.map((option, index) => (
                  <button key={index} type="button" className="option-chip" disabled={busy}
                    onClick={event => sendMessage(event, option)}>{option}</button>
                ))}
              </div>
            )}

            {!chatUsesDedicatedControl && <div className="composer-wrap">
              {pending?.kind === 'document' && <div className="upload-prompt"><Icon name="file" /><span>Waiting for: <b>{pending.label}</b></span></div>}
              <form className="composer" onSubmit={sendMessage}>
                <textarea value={text} onChange={e => setText(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }} placeholder={pending?.kind === 'detail' ? `Enter ${pending.label}…` : workflow ? 'Reply to Orqentra…' : 'Describe the application you want to complete…'} rows={1} disabled={busy} />
                <button className="send-button" disabled={busy || !text.trim()} aria-label="Send message"><Icon name="send" /></button>
              </form>
              <div className="composer-tools">
                <div className="upload-tools">
                  <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp" onChange={e => setFile(e.target.files?.[0] || null)} hidden />
                  <button className="tool-button" type="button" onClick={() => fileRef.current?.click()} disabled={!workflow || uploading}><Icon name="upload" /> Add document</button>
                  {file && <span className="selected-file"><Icon name="file" />{file.name}<button type="button" onClick={() => { setFile(null); if (fileRef.current) fileRef.current.value = ''; }}>×</button><button className="upload-now" type="button" onClick={uploadDocument} disabled={uploading}>{uploading ? 'Uploading…' : 'Upload'}</button></span>}
                </div>
                <span className="privacy-note">Your documents stay in the local Orqentra vault.</span>
              </div>
            </div>}
          </section>

          <aside className="activity-panel">
            <div className="panel-heading activity-heading">
              <div className="panel-title"><span className="heading-icon activity-icon"><Icon name="activity" /></span><div><h1>Live activity</h1><p>Background execution monitor</p></div></div>
              {workflow && <span className="progress-count">{doneCount}/{progressSteps.length}</span>}
            </div>
            {!workflow ? (
              <div className="activity-empty"><div className="empty-icon"><Icon name="activity" /></div><b>No active workflow</b><p>When you send a request, each agent action will appear here.</p>
                {recent.length > 0 && <div className="recent-list"><span>RECENT TASKS</span>{recent.slice(0, 5).map(item => <button key={item.id} onClick={() => selectWorkflow(item.id)}><span>{item.goal}</span><small>{item.status?.replaceAll('_', ' ')}</small></button>)}</div>}
              </div>
            ) : (
              <div className="activity-content">
                <div className="task-summary"><small>CURRENT REQUEST</small><b>{workflow.goal}</b><div className="summary-meta"><span>{workflow.service?.replaceAll('_', ' ')}</span><span>·</span><span>{workflow.task}</span></div></div>
                <div className="progress-track"><span style={{ width: `${progressSteps.length ? (doneCount / progressSteps.length) * 100 : 0}%` }} /></div>
                <div className="step-list">
                  {progressSteps.map((step, i) => <div className={`activity-step ${step.status || 'queued'}`} key={step.id}>
                    <div className="step-marker">{step.status === 'completed' ? <Icon name="check" /> : step.status === 'running' ? <span className="mini-spinner"/> : step.status === 'waiting' ? <Icon name="clock"/> : <span>{String(i + 1).padStart(2, '0')}</span>}</div>
                    <div className="step-copy"><b>{step.title}</b><small>{step.agent}</small>{step.detail && <p>{step.detail}</p>}</div>
                    <span className="step-status">{step.status === 'completed' ? 'Done' : step.status === 'running' ? 'Working' : step.status === 'waiting' ? 'Waiting' : 'Queued'}</span>
                  </div>)}
                </div>
                {workflow.current_page && (
                  <div className="browser-card">
                    <div className="browser-card-title"><Icon name="globe"/> Current portal page</div>
                    <b>{workflow.current_page.title || 'Application portal'}</b>
                    <a href={workflow.current_page.url} target="_blank" rel="noreferrer">{workflow.current_page.url}</a>
                    <PortalScreenshot key={workflow.id} workflowId={workflow.id} token={token} />
                    <small>{workflow.current_page.field_count} detected form controls</small>
                  </div>
                )}
                <div className="event-feed"><div className="feed-title">RECENT AGENT ACTIVITY</div>
                  {events.slice(-12).reverse().map((event, i) => <div className="event-item" key={`${event.created_at}-${i}`}><span className="event-dot"/><div><b>{event.message}</b><small>{formatTime(event.created_at)} · {event.kind.replaceAll('_', ' ')}</small></div></div>)}
                  {!events.length && <p className="empty-caption">Waiting for activity…</p>}
                </div>
                <div className="vault-mini"><div><Icon name="file"/><b>Document vault</b></div><span>{workflow.documents?.length || 0} document(s) added to this task</span></div>
                {workflow.status === 'completed' && <div className="complete-card"><Icon name="check"/><div><b>Workflow completed</b><p>Check the portal's acknowledgement or receipt.</p></div></div>}
                {workflow.status === 'error' && <div className="error-card"><b>Agent paused</b><p>{workflow.last_error}</p></div>}
              </div>
            )}
          </aside>
        </div>
      )}

      <footer><span>ORQENTRA 3.1</span><span>Encrypted · Document Intelligence · Human-in-the-loop</span></footer>
    </div>
  );
}
