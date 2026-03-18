interface FormErrorListProps {
  errors: string[];
}

export function FormErrorList({ errors }: FormErrorListProps) {
  if (errors.length === 0) {
    return null;
  }

  return (
    <div className="form-error-list" role="alert">
      <strong>Please fix the following:</strong>
      <ul>
        {errors.map((error) => (
          <li key={error}>{error}</li>
        ))}
      </ul>
    </div>
  );
}