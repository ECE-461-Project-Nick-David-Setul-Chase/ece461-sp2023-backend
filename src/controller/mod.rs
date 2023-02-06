mod bus_factor;

mod scores;
pub use scores::Scores;

mod metrics;
pub use metrics::Metrics;

use crate::{api::fetch::GithubRepositoryName, log, log::LogLevel};

use async_trait::async_trait;
use futures::future::join_all;
use std::{collections::HashMap, error::Error, path::Path, str::FromStr, sync::Arc};

#[async_trait]
/// The trait that defines scoring algorithms
trait Scorer {
    async fn score<P: AsRef<Path> + Send>(
        &self,
        path: P,
        url: &GithubRepositoryName,
    ) -> Result<f64, Box<dyn Error + Send + Sync>>;
}

#[derive(Debug, thiserror::Error)]
pub enum ControllerError {
    #[error("Do not know the `{0}` metric")]
    MetricParseError(String),
}

/// Run a set of scoring metrics and collect the results
///
/// Arguments:
///
/// * `path`: File path to the root of a locally cloned git repository
/// * `url`: Some object to use for API requests. Also used as the "name" of the project
/// * `to_run`: A list of `Metric`s to run on the repository.
/// * `log_level`: Passed to each metric to use for logging
///
/// TODO: see if having each metric open its own Repository is slower than running in sequence
/// with the same object. Alternatively, figure out how to share the Repository object
/// bewteen threads. The docs imply this is possible, but the type does not implement `Sync`.
pub async fn run_metrics<P: AsRef<Path> + Sync>(
    path: P,
    url: &GithubRepositoryName,
    to_run: Arc<Metrics>,
    weights: Arc<crate::input::Weights>,
) -> Result<Scores, Box<dyn Error + Send + Sync>> {
    log::log(LogLevel::Minimal, &format!("Starting analysis for {url}"));

    Ok(calculate_net_scores(
        Scores {
            url: url.to_string(),
            scores: join_all(to_run.iter().map(|metric| metric.score(&path, url)))
                .await
                .into_iter()
                .zip(to_run.iter())
                .map(|(score, metric)| Ok((*metric, score?)))
                .collect::<Result<HashMap<metrics::Metric, f64>, Box<dyn Error + Send + Sync>>>()?,
            ..Scores::default()
        },
        weights,
    ))
}

fn calculate_net_scores(scores: Scores, _weights: Arc<crate::input::Weights>) -> Scores {
    let mut sum = 0.;

    // add logic for weighted sum and normalization
    for (_metric, score) in scores.scores.iter() {
        sum += score;
    }

    Scores {
        net_score: sum,
        ..scores
    }
}
