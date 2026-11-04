use cranelift_codegen::{
	ir::{condcodes::IntCC, types, AbiParam, InstBuilder, MemFlagsData, UserFuncName},
	settings::{self, Configurable},
};
use cranelift_frontend::{FunctionBuilder, FunctionBuilderContext};
use cranelift_jit::{JITBuilder, JITModule};
use cranelift_module::{default_libcall_names, Linkage, Module};
use std::path::Path;

// Only this disposable harness converts compiler output into a function pointer.
// Caller borrows same-length readable inputs and disjoint writable output for
// the synchronous call; module remains owned until the call has returned.
pub struct Kernel {
	_module: JITModule,
	kind: String,
	pub entry: unsafe extern "C" fn(*const u8, *const u8, *mut u8, usize) -> usize,
	pub bytes: usize,
	pub address: usize,
}
impl Kernel {
	pub fn compile(op: &str, lanes: usize, artifact: Option<&Path>) -> Result<Self, String> {
		assert!([1, 2, 4].contains(&lanes));
		assert!(["i64add", "wrapadd", "axpy", "f64add", "boolnot"].contains(&op));
		let mut flags = settings::builder();
		flags.set("opt_level", "speed").unwrap();
		flags.set("is_pic", "false").unwrap();
		let isa = cranelift_native::builder()
			.map_err(str::to_string)?
			.finish(settings::Flags::new(flags))
			.map_err(|e| e.to_string())?;
		let mut module = JITModule::new(JITBuilder::with_isa(isa, default_libcall_names()));
		let mut ctx = module.make_context();
		let pointer = module.target_config().pointer_type();
		for _ in 0..4 {
			ctx.func.signature.params.push(AbiParam::new(pointer));
		}
		ctx.func.signature.returns.push(AbiParam::new(pointer));
		let id = module
			.declare_function("column_kernel", Linkage::Export, &ctx.func.signature)
			.map_err(|e| e.to_string())?;
		ctx.func.name = UserFuncName::user(0, id.as_u32());
		let mut fb = FunctionBuilderContext::new();
		{
			let mut b = FunctionBuilder::new(&mut ctx.func, &mut fb);
			let start = b.create_block();
			let vector = b.create_block();
			let vbody = b.create_block();
			let scalar = b.create_block();
			let sbody = b.create_block();
			let store_scalar = b.create_block();
			let done = b.create_block();
			let fault = b.create_block();
			b.append_block_params_for_function_params(start);
			for block in [vector, vbody, scalar, sbody, store_scalar, fault] {
				b.append_block_param(block, pointer);
			}
			b.switch_to_block(start);
			let args = b.block_params(start).to_vec();
			let (x, y, out, n) = (args[0], args[1], args[2], args[3]);
			let zero = b.ins().iconst(pointer, 0);
			b.ins().jump(vector, &[zero.into()]);
			let packed = op == "boolnot";
			let floating = op == "f64add";
			let unit = if packed { 1 } else { 8 };
			let width = if packed {
				if lanes == 1 {
					1
				} else {
					16
				}
			} else {
				lanes
			};
			b.switch_to_block(vector);
			let i = b.block_params(vector)[0];
			let left = b.ins().isub(n, i);
			let enough = b
				.ins()
				.icmp_imm_s(IntCC::UnsignedGreaterThanOrEqual, left, width as i64);
			b.ins()
				.brif(enough, vbody, &[i.into()], scalar, &[i.into()]);
			b.switch_to_block(vbody);
			let i = b.block_params(vbody)[0];
			if width == 1 {
				b.ins().jump(scalar, &[i.into()]);
			} else {
				let ty = if packed {
					types::I8X16
				} else if floating {
					if lanes == 2 {
						types::F64X2
					} else {
						types::F64X4
					}
				} else if lanes == 2 {
					types::I64X2
				} else {
					types::I64X4
				};
				let offset = b.ins().imul_imm_s(i, unit);
				let xp = b.ins().iadd(x, offset);
				let dst = b.ins().iadd(out, offset);
				let a = b.ins().load(ty, MemFlagsData::new(), xp, 0);
				let value = if packed {
					b.ins().bnot(a)
				} else if floating {
					let one = b.ins().f64const(1.0);
					let ones = b.ins().splat(ty, one);
					b.ins().fadd(a, ones)
				} else {
					let ones_scalar = b.ins().iconst(types::I64, 1);
					let ones = b.ins().splat(ty, ones_scalar);
					let (value, overflow) = if op == "axpy" {
						let yp = b.ins().iadd(y, offset);
						let rhs = b.ins().load(ty, MemFlagsData::new(), yp, 0);
						let product = b.ins().iadd(a, a);
						let sum = b.ins().iadd(product, rhs);
						let mul = b.ins().bxor(a, product);
						let l = b.ins().bxor(product, sum);
						let r = b.ins().bxor(rhs, sum);
						let add = b.ins().band(l, r);
						let sign = b.ins().bor(mul, add);
						let z = b.ins().iconst(types::I64, 0);
						let zeros = b.ins().splat(ty, z);
						let mask = b.ins().icmp(IntCC::SignedLessThan, sign, zeros);
						(sum, mask)
					} else {
						let sum = b.ins().iadd(a, ones);
						let max = b.ins().iconst(types::I64, i64::MAX);
						let maxes = b.ins().splat(ty, max);
						let mask = b.ins().icmp(IntCC::Equal, a, maxes);
						(sum, mask)
					};
					if op != "wrapadd" {
						let any = b.ins().vany_true(overflow);
						let valid = b.create_block();
						b.ins().brif(any, scalar, &[i.into()], valid, &[]);
						b.switch_to_block(valid);
					}
					value
				};
				b.ins().store(MemFlagsData::new(), value, dst, 0);
				let next = b.ins().iadd_imm_s(i, width as i64);
				b.ins().jump(vector, &[next.into()]);
			}
			b.switch_to_block(scalar);
			let i = b.block_params(scalar)[0];
			let more = b.ins().icmp(IntCC::UnsignedLessThan, i, n);
			b.ins().brif(more, sbody, &[i.into()], done, &[]);
			b.switch_to_block(sbody);
			let i = b.block_params(sbody)[0];
			let offset = b.ins().imul_imm_s(i, unit);
			let xp = b.ins().iadd(x, offset);
			let dst = b.ins().iadd(out, offset);
			let ty = if packed {
				types::I8
			} else if floating {
				types::F64
			} else {
				types::I64
			};
			let a = b.ins().load(ty, MemFlagsData::new(), xp, 0);
			let value = if packed {
				b.ins().bnot(a)
			} else if floating {
				let one = b.ins().f64const(1.0);
				b.ins().fadd(a, one)
			} else {
				let (value, overflow) = if op == "axpy" {
					let (product, mul) = b.ins().sadd_overflow(a, a);
					let yp = b.ins().iadd(y, offset);
					let rhs = b.ins().load(types::I64, MemFlagsData::new(), yp, 0);
					let (sum, add) = b.ins().sadd_overflow(product, rhs);
					let ov = b.ins().bor(mul, add);
					(sum, ov)
				} else {
					let one = b.ins().iconst(types::I64, 1);
					b.ins().sadd_overflow(a, one)
				};
				if op != "wrapadd" {
					let valid = b.create_block();
					b.ins().brif(overflow, fault, &[i.into()], valid, &[]);
					b.switch_to_block(valid);
				}
				value
			};
			b.ins().store(MemFlagsData::new(), value, dst, 0);
			let next = b.ins().iadd_imm_s(i, 1);
			b.ins().jump(scalar, &[next.into()]);
			// Unused block removed explicitly: no speculative write before overflow decision.
			b.switch_to_block(store_scalar);
			b.ins()
				.trap(cranelift_codegen::ir::TrapCode::user(1).unwrap());
			b.switch_to_block(fault);
			let i = b.block_params(fault)[0];
			b.ins().return_(&[i]);
			b.switch_to_block(done);
			b.ins().return_(&[n]);
			b.seal_all_blocks();
			b.finalize(module.target_config());
		}
		if let Some(path) = artifact {
			std::fs::create_dir_all(path).map_err(|e| e.to_string())?;
			std::fs::write(path.join("kernel.clif"), ctx.func.display().to_string())
				.map_err(|e| e.to_string())?;
		}
		module
			.define_function(id, &mut ctx)
			.map_err(|e| format!("{e:?}"))?;
		let machine = ctx.compiled_code().unwrap().code_buffer();
		let bytes = machine.len();
		if let Some(path) = artifact {
			std::fs::write(path.join("kernel.bin"), machine).map_err(|e| e.to_string())?;
		}
		module.finalize_definitions().map_err(|e| e.to_string())?;
		let ptr = module.get_finalized_function(id);
		let entry = unsafe {
			std::mem::transmute::<
				*const u8,
				unsafe extern "C" fn(*const u8, *const u8, *mut u8, usize) -> usize,
			>(ptr)
		};
		Ok(Self {
			_module: module,
			kind: op.to_string(),
			entry,
			bytes,
			address: ptr as usize,
		})
	}
	pub fn i64(&self, x: &[i64], y: &[i64], out: &mut [i64]) -> usize {
		assert!(["i64add", "wrapadd", "axpy"].contains(&self.kind.as_str()));
		assert_eq!(x.len(), y.len());
		assert_eq!(x.len(), out.len());
		unsafe {
			(self.entry)(
				x.as_ptr().cast(),
				y.as_ptr().cast(),
				out.as_mut_ptr().cast(),
				x.len(),
			)
		}
	}
	pub fn f64(&self, x: &[f64], out: &mut [f64]) -> usize {
		assert_eq!(self.kind, "f64add");
		assert_eq!(x.len(), out.len());
		unsafe {
			(self.entry)(
				x.as_ptr().cast(),
				x.as_ptr().cast(),
				out.as_mut_ptr().cast(),
				x.len(),
			)
		}
	}
	pub fn packed(&self, x: &[u8], out: &mut [u8]) -> usize {
		assert_eq!(self.kind, "boolnot");
		assert_eq!(x.len(), out.len());
		unsafe { (self.entry)(x.as_ptr(), x.as_ptr(), out.as_mut_ptr(), x.len()) }
	}
}
