"""Make an auditable scratch patch at the fixed source sites, never change the fork base."""
import pathlib,re,shutil,subprocess,os
P=pathlib.Path(__file__).resolve().parent
R=pathlib.Path(os.environ.get('RNX_PROFILE_SCRATCH','/tmp/rune-0169-profile'))
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()=='bb8e69372353c50e271c9f115bc771c77aa6b83e'
assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain'],text=True),'scratch already dirty; refuse reapplying'
p=R/'crates/rune/Cargo.toml';p.write_text(p.read_text().replace('[features]','[features]\nregistration-profile = ["std"]\nregistration-omit-control = ["registration-profile"]',1))
p=R/'crates/rune/src/lib.rs';p.write_text(p.read_text()+'\n#[cfg(feature = "registration-profile")]\npub mod registration_profile;\n')
shutil.copyfile(P/'registration_profile.rs',R/'crates/rune/src/registration_profile.rs')
p=R/'crates/rune/src/compile/context.rs';s=p.read_text()
a=s.index('    pub fn with_config(');b=s.index('\n    /// Construct a new collection',a)
section=s[a:b];modules=[]
pattern=r'        this.install\((crate::modules::(.*?)::module\(.*?\)\?)\)\?;'
def replace(m):
 name=m[2];expr=m[1];modules.append(name)
 before='#[cfg(not(feature = "registration-omit-control"))]' if name=="collections::hash_map" else ""
 after='#[cfg(feature = "registration-omit-control")] let _ = module;' if name=="collections::hash_map" else ""
 result=f'''        #[cfg(feature = "registration-profile")]
        {{
            crate::registration_profile::set_module("{name}");
            let module = {{ let _mark = crate::registration_profile::mark("construct"); {expr} }};
            let _mark = crate::registration_profile::mark("install");
            {before}
            this.install(module)?;
            {after}
        }}
        #[cfg(not(feature = "registration-profile"))]
{m[0]}'''
 return "\n".join(line for line in result.split("\n") if line.strip())
section=re.sub(pattern,replace,section);assert len(modules)==34,modules
s=s[:a]+section+s[b:]
# Each loop stays in place and order: wrapper scope only for non-overlapping stage clocks.
a=s.index('        tracing::trace!("module");',s.index('    pub fn install<M>'))
b=s.index('\n        Ok(())',a)
section=s[a:b]
starts=list(re.finditer(r'        tracing::trace!\((?:"module"|(?:types|traits|items|associated|trait_impls|reexports|construct) =)',section));assert len(starts)==8
labels=['module','types','traits','items','associated','trait_impls','reexports','construct']
pieces=[]
for i,(m,label) in enumerate(zip(starts,labels)):
 end=starts[i+1].start() if i+1<len(starts) else len(section)
 pieces.append('        {\n            #[cfg(feature = "registration-profile")]\n            let _stage = crate::registration_profile::mark("'+label+'");\n'+section[m.start():end]+'\n        }\n')
s=s[:a]+''.join(pieces)+s[b:]
# Observed event counts, not allocation-type guesses.
for marker,index in [('        let function = ModuleFunction {',2),('    fn install_meta(&mut self, meta: ContextMeta) -> Result<(), ContextError> {',0),('    fn install_trait_impl(&mut self, i: &ModuleTraitImpl) -> Result<(), ContextError> {',1)]:
 assert s.count(marker)==1
 if index==2:s=s.replace(marker,'        #[cfg(feature = "registration-profile")]\n        crate::registration_profile::hit(2);\n'+marker,1)
 else:s=s.replace(marker,marker+f'\n        #[cfg(feature = "registration-profile")]\n        crate::registration_profile::hit({index});',1)
marker='    pub fn runtime(&self) -> alloc::Result<RuntimeContext> {'
inventory='''    /// Diagnostic inventory for the isolated registration probe.
    #[cfg(feature = "registration-profile")]
    pub fn registration_inventory(&self) -> std::vec::Vec<std::string::String> {
        let mut rows = std::vec::Vec::new();
        rows.push(std::format!("defaults:{}",self.has_default_modules));
'''
for field in ['functions','types','traits','macros','attribute_macros','constants','construct']:
 inventory+=f'        for (h, _) in self.{field}.iter() {{ rows.push(std::format!("{field}:{{:?}}",h)); }}\n'
inventory+='''        for m in &self.meta { rows.push(std::format!("meta:{:?}:{:?}:{:?}",m.hash,m.item,core::mem::discriminant(&m.kind))); }
        rows.sort(); rows
    }

'''
marker='    /// Construct a runtime context used'
assert marker in s;s=s.replace(marker,inventory+marker,1);p.write_text(s)
(P/'expected_modules.json').write_text(__import__('json').dumps(modules,indent=2)+'\n')
patch=subprocess.check_output(['git','-C',str(R),'diff','--','crates/rune/Cargo.toml','crates/rune/src/lib.rs','crates/rune/src/compile/context.rs'])
(P/'registration.patch').write_bytes(patch)
print('34 modules, 8 install stages, 3 event-count sites; new collector copied separately')
