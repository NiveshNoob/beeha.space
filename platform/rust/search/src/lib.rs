use pyo3::prelude::*;

/// Normalize text for a future search index; Python search remains the fallback.
#[pyfunction]
fn normalize(value: &str) -> String {
    value.to_lowercase().split_whitespace().collect::<Vec<_>>().join(" ")
}

#[pymodule]
fn beeha_search(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(normalize, module)?)?;
    Ok(())
}
