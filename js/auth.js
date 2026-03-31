const ADMIN_SESSION_KEY = 'nexus_admin_session';
const USER_SESSION_KEY = 'nexus_user_session';

const ADMIN_CREDENTIALS = {
    username: 'admin',
    email: 'admin@nexuspanel.com',
    password: 'admin123',
    role: 'super_admin'
};

function adminLogin(username, password) {
    if ((username === ADMIN_CREDENTIALS.username || username === ADMIN_CREDENTIALS.email) 
        && password === ADMIN_CREDENTIALS.password) {
        const session = {
            username: ADMIN_CREDENTIALS.username,
            email: ADMIN_CREDENTIALS.email,
            role: ADMIN_CREDENTIALS.role,
            loginTime: new Date().toISOString(),
            isAdmin: true
        };
        localStorage.setItem(ADMIN_SESSION_KEY, JSON.stringify(session));
        return { success: true, admin: session };
    }
    return { success: false, message: 'Invalid admin credentials' };
}

function getCurrentAdmin() {
    const session = localStorage.getItem(ADMIN_SESSION_KEY);
    if (session) {
        try { return JSON.parse(session); } catch(e) { return null; }
    }
    return null;
}

function isAdminLoggedIn() {
    return getCurrentAdmin() !== null;
}

function adminLogout() {
    localStorage.removeItem(ADMIN_SESSION_KEY);
    window.location.href = '../index.html';
}

function requireAdminAuth() {
    if (!isAdminLoggedIn()) {
        window.location.href = '../index.html';
        return false;
    }
    return true;
}

function userLogin(username, password) {
    initData();
    const user = globalUserCredentials.find(u => 
        (u.username === username || u.email === username) && u.password === password
    );
    
    if (user) {
        const fullUser = globalUsers.find(u => u.id === user.userId);
        const session = {
            userId: user.userId,
            username: user.username,
            email: user.email,
            role: user.role || 'user',
            loginTime: new Date().toISOString(),
            isAdmin: false
        };
        localStorage.setItem(USER_SESSION_KEY, JSON.stringify(session));
        return { success: true, user: session };
    }
    return { success: false, message: 'Invalid user credentials' };
}

function getCurrentUser() {
    const session = localStorage.getItem(USER_SESSION_KEY);
    if (session) {
        try { return JSON.parse(session); } catch(e) { return null; }
    }
    return null;
}

function isUserLoggedIn() {
    return getCurrentUser() !== null;
}

function userLogout() {
    localStorage.removeItem(USER_SESSION_KEY);
    window.location.href = '../index.html';
}

function requireUserAuth() {
    if (!isUserLoggedIn()) {
        window.location.href = '../index.html';
        return false;
    }
    return true;
}