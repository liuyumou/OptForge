//! Isolated adapter: reuse original geometry while admitting an exact host step.
use optimizer_lp::{LinearProgram, LpSettings};
use std::ops::Deref;

pub struct Engine<'a> {
    base: optimizer_lp::Engine<'a>,
    settings: LpSettings,
    exact_step: Option<f64>,
}
impl<'a> Engine<'a> {
    pub(crate) fn from_device(base: optimizer_lp::Engine<'a>, settings: LpSettings) -> Self {
        let step = base.step();
        Self {
            base,
            settings,
            exact_step: Some(step),
        }
    }
    pub fn new(program: &'a LinearProgram, settings: LpSettings) -> Self {
        Self {
            base: optimizer_lp::Engine::new(program, settings),
            settings,
            exact_step: None,
        }
    }
    pub(crate) fn without_spectral(program: &'a LinearProgram, settings: LpSettings) -> Self {
        let mut cheap = settings;
        cheap.power_iterations = 0;
        Self {
            base: optimizer_lp::Engine::new(program, cheap),
            settings,
            exact_step: Some(1.),
        }
    }
    pub(crate) fn assign_exact_step(&mut self, step: f64) {
        self.exact_step = Some(step);
    }
    pub fn settings(&self) -> LpSettings {
        self.settings
    }
    pub fn step(&self) -> f64 {
        self.exact_step.unwrap_or_else(|| self.base.step())
    }
    pub fn step_once(&self, x: &[f64], y: &[f64], weight: f64) -> (Vec<f64>, Vec<f64>) {
        if self.exact_step.is_some() {
            crate::host::step_once(self, x, y, weight)
        } else {
            self.base.step_once(x, y, weight)
        }
    }
}
impl<'a> Deref for Engine<'a> {
    type Target = optimizer_lp::Engine<'a>;
    fn deref(&self) -> &Self::Target {
        &self.base
    }
}
