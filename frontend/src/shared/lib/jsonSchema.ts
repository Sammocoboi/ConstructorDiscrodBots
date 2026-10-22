import type { JsonSchema, JsonSchemaProperty } from '../api/types'

export function propertyDefault(property: JsonSchemaProperty): unknown {
  if (property.default !== undefined) return property.default
  if (property.enum?.length) return property.enum[0].value
  switch (property.type) {
    case 'boolean':
      return false
    case 'number':
    case 'integer':
      return property.minimum ?? 0
    case 'array':
      return []
    default:
      return ''
  }
}

export function schemaDefaults(schema: JsonSchema): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(schema.properties).map(([key, property]) => [
      key,
      propertyDefault(property),
    ]),
  )
}

export function isFieldVisible(
  _key: string,
  _property: JsonSchemaProperty,
  _values: Record<string, unknown>,
) {
  return true
}
