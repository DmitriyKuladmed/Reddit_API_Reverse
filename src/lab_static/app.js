(function(){
	// Lightweight obfuscation: split strings and assemble at runtime
	const j = (a,b)=>a+b;
	const H = (s)=>{
		let A=0; for(let i=0;i<s.length;i++){A=((A<<5)-A)+s.charCodeAt(i); A>>>0} return A.toString(16)
	};
	const pathT = j('/api','/token');
	const pathP = j('/api','/posts');

	async function fetchToken(){
		const r = await fetch(pathT,{method:'POST'});
		if(r.status===429){
			const ra=r.headers.get('Retry-After')||'1';
			await new Promise(z=>setTimeout(z, parseInt(ra,10)*1000));
			return fetchToken();
		}
		if(!r.ok) throw new Error('token_fail');
		const d = await r.json();
		return d.token;
	}

	async function fetchPosts(token){
		const u = new URL(pathP, window.location.origin);
		u.searchParams.set('subreddit','technology');
		u.searchParams.set('limit','5');
		const r = await fetch(u.toString(), { headers: { 'Authorization': 'Bearer '+token }});
		if(r.status===429){
			const ra=r.headers.get('Retry-After')||'1';
			await new Promise(z=>setTimeout(z, parseInt(ra,10)*1000));
			return fetchPosts(token);
		}
		if(!r.ok) throw new Error('posts_fail');
		return r.json();
	}

	document.getElementById('btn').addEventListener('click', async ()=>{
		const out = document.getElementById('out');
		out.textContent = 'Loading...';
		try{
			const t = await fetchToken();
			const data = await fetchPosts(t);
			out.textContent = JSON.stringify(data, null, 2);
		}catch(e){
			out.textContent = 'Error: '+ e;
		}
	});
})();
