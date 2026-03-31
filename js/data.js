// Add these functions to js/data.js

// Function to load OTPs from the bot's data file
// You need to serve the data folder via your web server
async function loadOtpsFromBot() {
    try {
        // This assumes your data folder is accessible via web server
        const response = await fetch('../data/otp_logs.json');
        if (response.ok) {
            const otps = await response.json();
            localStorage.setItem('nexus_all_otp_records', JSON.stringify(otps));
            return otps;
        }
    } catch (error) {
        console.log('Could not load OTPs from bot, using local storage');
    }
    
    // Fallback to local storage
    const stored = localStorage.getItem('nexus_all_otp_records');
    return stored ? JSON.parse(stored) : [];
}

// Function to match OTPs with user's numbers
function getOtpsForUser(userId) {
    const allOtps = JSON.parse(localStorage.getItem('nexus_all_otp_records') || '[]');
    const userNumbers = JSON.parse(localStorage.getItem('nexus_analytics_numbers') || '[]');
    
    // Get all numbers allocated to this user
    const userNumberEntries = userNumbers.filter(n => n.userId === userId);
    const userPhoneLast4s = [];
    
    userNumberEntries.forEach(entry => {
        entry.numbers.forEach(number => {
            // Extract last 4 digits from each allocated number
            const cleanNumber = number.replace(/\D/g, '');
            if (cleanNumber.length >= 4) {
                userPhoneLast4s.push(cleanNumber.slice(-4));
            }
        });
    });
    
    // Filter OTPs that match any of the user's phone last 4 digits
    return allOtps.filter(otp => userPhoneLast4s.includes(otp.phone_last4));
}

// Update user dashboard to show real OTPs
function updateUserWithRealOtps() {
    const currentUser = getCurrentUser();
    if (!currentUser) return;
    
    const userOtps = getOtpsForUser(currentUser.userId);
    
    // Save to user's local storage for quick access
    localStorage.setItem(`nexus_otp_${currentUser.userId}`, JSON.stringify(userOtps));
    
    return userOtps;
}

// Add this function to js/data.js
function createUserWithPassword(username, password, email = null) {
    const newId = crypto.randomUUID();
    const today = getTodayStr();
    const userEmail = email || `${username}@nexuspanel.com`;
    
    // Check if username already exists
    if (globalUsers.some(u => u.username.toLowerCase() === username.toLowerCase())) {
        return { success: false, message: 'Username already exists' };
    }
    
    globalUsers.push({ 
        id: newId, 
        username, 
        email: userEmail, 
        createdAt: today 
    });
    
    globalUserCredentials.push({
        userId: newId,
        username: username,
        email: userEmail,
        password: password,
        createdAt: today,
        role: 'user'
    });
    
    if (!globalRequests.some(r => r.userId === newId && r.date === today)) {
        globalRequests.push({ id: crypto.randomUUID(), userId: newId, date: today, count: 0 });
    }
    
    saveToLocal();
    return { success: true, userId: newId, password: password };
}

// Shared data management - persists across pages via localStorage

let globalUsers = [];
let globalRequests = [];
let globalUserCredentials = [];

function getUsers() { return globalUsers; }
function getAllRequests() { return globalRequests; }
function getUserCredentials() { return globalUserCredentials; }
function getRequestsByUserAndDate(userId, date) { 
    return globalRequests.find(r => r.userId === userId && r.date === date); 
}
function getRequestsInRange(userId, start, end) { 
    return globalRequests.filter(r => r.userId === userId && r.date >= start && r.date <= end).sort((a,b)=>a.date.localeCompare(b.date)); 
}
function getTodayStr() { return new Date().toISOString().slice(0,10); }

function saveToLocal() {
    localStorage.setItem('nexus_users', JSON.stringify(globalUsers));
    localStorage.setItem('nexus_requests', JSON.stringify(globalRequests));
    localStorage.setItem('nexus_credentials', JSON.stringify(globalUserCredentials));
}

function initData() {
    const storedUsers = localStorage.getItem('nexus_users');
    const storedLogs = localStorage.getItem('nexus_requests');
    const storedCredentials = localStorage.getItem('nexus_credentials');
    
    if (storedUsers) {
        globalUsers = JSON.parse(storedUsers);
        globalRequests = JSON.parse(storedLogs || '[]');
        globalUserCredentials = JSON.parse(storedCredentials || '[]');
    } else {
        globalUsers = [
            { id: 'u1', username: 'emily_chen', email: 'emily@example.com', createdAt: getTodayStr() },
            { id: 'u2', username: 'marcus_v', email: 'marcus@example.com', createdAt: getTodayStr() },
            { id: 'u3', username: 'sophia_laurent', email: 'sophia@example.com', createdAt: getTodayStr() },
            { id: 'u4', username: 'james_m', email: 'james@example.com', createdAt: getTodayStr() }
        ];
        
        globalUserCredentials = globalUsers.map(user => ({
            userId: user.id,
            username: user.username,
            email: user.email,
            password: 'password123',
            createdAt: getTodayStr(),
            role: 'user'
        }));
        
        globalRequests = [];
        for(let i=0; i<=10; i++) {
            let d = new Date(); 
            d.setDate(d.getDate() - i);
            let dateKey = d.toISOString().slice(0,10);
            globalUsers.forEach(user => {
                let randCount = Math.floor(Math.random() * 25) + (i===0 ? 5 : 2);
                globalRequests.push({ id: crypto.randomUUID(), userId: user.id, date: dateKey, count: randCount });
            });
        }
        saveToLocal();
    }
}

function createUser(username, email, password = null) {
    const newId = crypto.randomUUID();
    const today = getTodayStr();
    const userPassword = password || `pass${Math.floor(Math.random() * 10000)}`;
    
    globalUsers.push({ id: newId, username, email, createdAt: today });
    globalUserCredentials.push({
        userId: newId,
        username: username,
        email: email,
        password: userPassword,
        createdAt: today,
        role: 'user'
    });
    
    if (!globalRequests.some(r => r.userId === newId && r.date === today)) {
        globalRequests.push({ id: crypto.randomUUID(), userId: newId, date: today, count: 0 });
    }
    
    saveToLocal();
    return { userId: newId, password: userPassword };
}

function updateUser(id, username, email) {
    const user = globalUsers.find(u => u.id === id);
    if (user) { 
        user.username = username; 
        user.email = email; 
        const cred = globalUserCredentials.find(c => c.userId === id);
        if (cred) { cred.username = username; cred.email = email; }
        saveToLocal(); 
    }
}

function deleteUserById(id) {
    globalUsers = globalUsers.filter(u => u.id !== id);
    globalRequests = globalRequests.filter(r => r.userId !== id);
    globalUserCredentials = globalUserCredentials.filter(c => c.userId !== id);
    saveToLocal();
}

function incrementRequestToday(userId) {
    const today = getTodayStr();
    const existing = globalRequests.find(r => r.userId === userId && r.date === today);
    if (existing) existing.count += 1;
    else globalRequests.push({ id: crypto.randomUUID(), userId, date: today, count: 1 });
    saveToLocal();
}

function populateUserSelect(selectId) {
    const select = document.getElementById(selectId);
    if (select) {
        select.innerHTML = '<option value="">-- Select User --</option>' + 
            globalUsers.map(u => `<option value="${u.id}">${escapeHtml(u.username)}</option>`).join('');
    }
}

function escapeHtml(str) { 
    if(!str) return ''; 
    return str.replace(/[&<>]/g, function(m){
        if(m==='&') return '&amp;'; 
        if(m==='<') return '&lt;'; 
        if(m==='>') return '&gt;'; 
        return m;
    }); 
}
