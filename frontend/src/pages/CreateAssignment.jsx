import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  configureAssignment,
  createAssignment,
  publishAssignment,
} from "../api/assignments";
import { ApiError } from "../api/client";

const emptyIoCase = () => ({
  name: "",
  stdin: "",
  expected_stdout: "",
  points: 100,
  visibility: "hidden",
  order_index: 1,
});

export default function CreateAssignment() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: "",
    description: "",
    instructions: "",
    ioWeight: 100,
    unitWeight: 0,
    staticWeight: 0,
    maxRuntimeMs: 2000,
    maxMemoryKb: 128000,
    unitName: "unit tests",
    unitCode: "",
    unitPoints: 100,
    unitVisibility: "hidden",
    requiredFunctions: "",
    forbiddenImports: "",
    maxComplexity: 10,
    staticPoints: 100,
    publishNow: true,
  });
  const [ioCases, setIoCases] = useState([emptyIoCase()]);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const weightTotal = useMemo(
    () =>
      Number(form.ioWeight) +
      Number(form.unitWeight) +
      Number(form.staticWeight),
    [form.ioWeight, form.unitWeight, form.staticWeight],
  );

  function updateField(event) {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  function updateIoCase(index, field, value) {
    setIoCases((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              [field]: value,
            }
          : item,
      ),
    );
  }

  function addIoCase() {
    setIoCases((current) => [
      ...current,
      {
        ...emptyIoCase(),
        points: 0,
        order_index: current.length + 1,
      },
    ]);
  }

  function removeIoCase(index) {
    setIoCases((current) =>
      current
        .filter((_, itemIndex) => itemIndex !== index)
        .map((item, itemIndex) => ({
          ...item,
          order_index: itemIndex + 1,
        })),
    );
  }

  function commaList(value) {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function validate() {
    if (weightTotal !== 100) {
      return "IO, unit, and static weights must total exactly 100.";
    }

    if (Number(form.ioWeight) > 0) {
      if (ioCases.length === 0) {
        return "Add at least one IO test when IO grading has a positive weight.";
      }

      if (
        ioCases.some(
          (item) =>
            !item.name.trim() ||
            item.expected_stdout === "" ||
            Number(item.points) <= 0,
        )
      ) {
        return "Every IO test needs a name, expected output, and positive points.";
      }
    }

    if (Number(form.unitWeight) > 0 && !form.unitCode.trim()) {
      return "Provide unit-test code when unit grading has a positive weight.";
    }

    if (
      Number(form.staticWeight) > 0 &&
      commaList(form.requiredFunctions).length === 0 &&
      commaList(form.forbiddenImports).length === 0 &&
      !form.maxComplexity
    ) {
      return "Configure at least one static-analysis rule.";
    }

    return "";
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const validationError = validate();

    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const assignment = await createAssignment({
        title: form.title.trim(),
        description: form.description.trim(),
        instructions: form.instructions.trim(),
        grading_policy: {
          io_weight: Number(form.ioWeight),
          unit_weight: Number(form.unitWeight),
          static_weight: Number(form.staticWeight),
        },
        execution_limits: {
          max_runtime_ms: Number(form.maxRuntimeMs),
          max_memory_kb: Number(form.maxMemoryKb),
        },
      });

      const configuration = {};

      if (Number(form.ioWeight) > 0) {
        configuration.io_test_cases = ioCases.map((item, index) => ({
          name: item.name.trim(),
          stdin: item.stdin,
          expected_stdout: item.expected_stdout,
          points: Number(item.points),
          visibility: item.visibility,
          order_index: index + 1,
        }));
      }

      if (Number(form.unitWeight) > 0) {
        configuration.unit_test_spec = {
          name: form.unitName.trim() || "unit tests",
          test_code: form.unitCode,
          points: Number(form.unitPoints),
          visibility: form.unitVisibility,
        };
      }

      if (Number(form.staticWeight) > 0) {
        configuration.static_analysis_rules = {
          required_functions: commaList(form.requiredFunctions),
          forbidden_imports: commaList(form.forbiddenImports),
          max_cyclomatic_complexity: Number(form.maxComplexity),
          points: Number(form.staticPoints),
        };
      }

      await configureAssignment(assignment.id, configuration);

      if (form.publishNow) {
        await publishAssignment(assignment.id);
      }

      navigate("/instructor", {
        replace: true,
        state: {
          flash: form.publishNow
            ? "Assignment created and published."
            : "Assignment created as a draft.",
        },
      });
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Unable to create the assignment.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="workflow-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">Instructor workflow</div>
          <h1>Create assignment</h1>
          <p className="muted">
            Create the draft, configure deterministic grading, and publish it
            in one guided form.
          </p>
        </div>
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}

      <form className="workflow-form" onSubmit={handleSubmit}>
        <section className="form-section">
          <div className="section-heading">
            <span>01</span>
            <div>
              <h2>Assignment details</h2>
              <p>What should the student build?</p>
            </div>
          </div>

          <div className="form-grid">
            <label className="field-span-2">
              <span>Title</span>
              <input
                name="title"
                onChange={updateField}
                placeholder="Functions and Control Flow"
                required
                value={form.title}
              />
            </label>

            <label className="field-span-2">
              <span>Description</span>
              <textarea
                name="description"
                onChange={updateField}
                placeholder="Implement a Python solution for the exercise."
                required
                rows={3}
                value={form.description}
              />
            </label>

            <label className="field-span-2">
              <span>Instructions</span>
              <textarea
                name="instructions"
                onChange={updateField}
                placeholder="Optional detailed instructions shown to students."
                rows={4}
                value={form.instructions}
              />
            </label>
          </div>
        </section>

        <section className="form-section">
          <div className="section-heading">
            <span>02</span>
            <div>
              <h2>Grading policy</h2>
              <p>Weights must total exactly 100.</p>
            </div>
            <div
              className={`weight-total ${
                weightTotal === 100 ? "weight-valid" : "weight-invalid"
              }`}
            >
              {weightTotal}%
            </div>
          </div>

          <div className="form-grid form-grid-3">
            <label>
              <span>IO weight</span>
              <input
                min="0"
                max="100"
                name="ioWeight"
                onChange={updateField}
                type="number"
                value={form.ioWeight}
              />
            </label>

            <label>
              <span>Unit-test weight</span>
              <input
                min="0"
                max="100"
                name="unitWeight"
                onChange={updateField}
                type="number"
                value={form.unitWeight}
              />
            </label>

            <label>
              <span>Static-analysis weight</span>
              <input
                min="0"
                max="100"
                name="staticWeight"
                onChange={updateField}
                type="number"
                value={form.staticWeight}
              />
            </label>
          </div>
        </section>

        {Number(form.ioWeight) > 0 ? (
          <section className="form-section">
            <div className="section-heading">
              <span>03</span>
              <div>
                <h2>IO tests</h2>
                <p>Add visible examples or hidden grading cases.</p>
              </div>
              <button
                className="button button-secondary"
                onClick={addIoCase}
                type="button"
              >
                + Add test
              </button>
            </div>

            <div className="test-case-list">
              {ioCases.map((testCase, index) => (
                <div className="test-case-card" key={`io-${index + 1}`}>
                  <div className="test-case-header">
                    <strong>Test {index + 1}</strong>
                    {ioCases.length > 1 ? (
                      <button
                        className="text-button danger"
                        onClick={() => removeIoCase(index)}
                        type="button"
                      >
                        Remove
                      </button>
                    ) : null}
                  </div>

                  <div className="form-grid">
                    <label>
                      <span>Name</span>
                      <input
                        onChange={(event) =>
                          updateIoCase(index, "name", event.target.value)
                        }
                        placeholder="basic addition"
                        required
                        value={testCase.name}
                      />
                    </label>

                    <label>
                      <span>Visibility</span>
                      <select
                        onChange={(event) =>
                          updateIoCase(index, "visibility", event.target.value)
                        }
                        value={testCase.visibility}
                      >
                        <option value="visible">Visible</option>
                        <option value="hidden">Hidden</option>
                      </select>
                    </label>

                    <label>
                      <span>stdin</span>
                      <textarea
                        onChange={(event) =>
                          updateIoCase(index, "stdin", event.target.value)
                        }
                        placeholder="2 3"
                        rows={3}
                        value={testCase.stdin}
                      />
                    </label>

                    <label>
                      <span>Expected stdout</span>
                      <textarea
                        onChange={(event) =>
                          updateIoCase(
                            index,
                            "expected_stdout",
                            event.target.value,
                          )
                        }
                        placeholder="5"
                        required
                        rows={3}
                        value={testCase.expected_stdout}
                      />
                    </label>

                    <label>
                      <span>Points</span>
                      <input
                        min="1"
                        onChange={(event) =>
                          updateIoCase(index, "points", event.target.value)
                        }
                        required
                        type="number"
                        value={testCase.points}
                      />
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {Number(form.unitWeight) > 0 ? (
          <section className="form-section">
            <div className="section-heading">
              <span>04</span>
              <div>
                <h2>Unit tests</h2>
                <p>These execute inside the isolated grading environment.</p>
              </div>
            </div>

            <div className="form-grid">
              <label>
                <span>Name</span>
                <input
                  name="unitName"
                  onChange={updateField}
                  value={form.unitName}
                />
              </label>

              <label>
                <span>Visibility</span>
                <select
                  name="unitVisibility"
                  onChange={updateField}
                  value={form.unitVisibility}
                >
                  <option value="visible">Visible</option>
                  <option value="hidden">Hidden</option>
                </select>
              </label>

              <label className="field-span-2">
                <span>Test code</span>
                <textarea
                  className="code-input"
                  name="unitCode"
                  onChange={updateField}
                  placeholder="assert solve(2, 3) == 5"
                  rows={6}
                  value={form.unitCode}
                />
              </label>

              <label>
                <span>Points</span>
                <input
                  min="1"
                  name="unitPoints"
                  onChange={updateField}
                  type="number"
                  value={form.unitPoints}
                />
              </label>
            </div>
          </section>
        ) : null}

        {Number(form.staticWeight) > 0 ? (
          <section className="form-section">
            <div className="section-heading">
              <span>05</span>
              <div>
                <h2>Static analysis</h2>
                <p>Comma-separate function and import names.</p>
              </div>
            </div>

            <div className="form-grid">
              <label>
                <span>Required functions</span>
                <input
                  name="requiredFunctions"
                  onChange={updateField}
                  placeholder="solve, validate"
                  value={form.requiredFunctions}
                />
              </label>

              <label>
                <span>Forbidden imports</span>
                <input
                  name="forbiddenImports"
                  onChange={updateField}
                  placeholder="os, subprocess"
                  value={form.forbiddenImports}
                />
              </label>

              <label>
                <span>Maximum complexity</span>
                <input
                  min="1"
                  name="maxComplexity"
                  onChange={updateField}
                  type="number"
                  value={form.maxComplexity}
                />
              </label>

              <label>
                <span>Points</span>
                <input
                  min="1"
                  name="staticPoints"
                  onChange={updateField}
                  type="number"
                  value={form.staticPoints}
                />
              </label>
            </div>
          </section>
        ) : null}

        <section className="form-section">
          <div className="section-heading">
            <span>06</span>
            <div>
              <h2>Execution limits</h2>
              <p>Sandbox constraints applied during dynamic grading.</p>
            </div>
          </div>

          <div className="form-grid">
            <label>
              <span>Runtime limit (ms)</span>
              <input
                min="100"
                name="maxRuntimeMs"
                onChange={updateField}
                type="number"
                value={form.maxRuntimeMs}
              />
            </label>

            <label>
              <span>Memory limit (KB)</span>
              <input
                min="16000"
                name="maxMemoryKb"
                onChange={updateField}
                type="number"
                value={form.maxMemoryKb}
              />
            </label>
          </div>
        </section>

        <div className="form-actions">
          <label className="checkbox-field">
            <input
              checked={form.publishNow}
              name="publishNow"
              onChange={updateField}
              type="checkbox"
            />
            <span>Publish immediately after configuration</span>
          </label>

          <div className="action-row">
            <button
              className="button button-ghost"
              onClick={() => navigate("/instructor")}
              type="button"
            >
              Cancel
            </button>
            <button
              className="button button-primary"
              disabled={submitting}
              type="submit"
            >
              {submitting
                ? "Creating assignment…"
                : form.publishNow
                  ? "Create & publish"
                  : "Create draft"}
            </button>
          </div>
        </div>
      </form>
    </section>
  );
}
