"""
Dynamic AI Tools - Auto-generating function schemas from database models
This addresses the second question about AI tools updating automatically as the database evolves.
"""

import logging
from typing import Dict, List, Any, Optional, Type
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from app.models import (
    Event, TicketType, EventCustomField, DynamicFieldDefinition, 
    DynamicFieldValue, User
)

class DynamicToolGenerator:
    """Generate AI tool schemas automatically from database models"""
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
    
    def generate_dynamic_tools(self) -> List[Dict[str, Any]]:
        """Generate AI tools based on current database schema and dynamic fields"""
        tools = []
        
        # Generate core model tools
        tools.extend(self._generate_model_tools())
        
        # Generate dynamic field tools
        tools.extend(self._generate_dynamic_field_tools())
        
        return tools
    
    def _generate_model_tools(self) -> List[Dict[str, Any]]:
        """Generate tools for core database models"""
        tools = []
        
        # Generate create/update tools for each model
        for model_class in [Event, TicketType]:
            tools.append(self._generate_create_tool(model_class))
            tools.append(self._generate_update_tool(model_class))
        
        return tools
    
    def _generate_create_tool(self, model_class: Type) -> Dict[str, Any]:
        """Generate a create tool for a specific model"""
        model_name = model_class.__name__
        table_name = model_class.__tablename__
        
        # Inspect the model to get its columns
        inspector = inspect(model_class)
        properties = {}
        required_fields = []
        
        for column in inspector.columns:
            column_name = column.name
            
            # Skip internal fields
            if column_name in ['id', 'created_at', 'updated_at', 'created_by']:
                continue
            
            # Determine JSON schema type
            column_type = self._sqlalchemy_to_json_type(column.type)
            
            property_def = {
                "type": column_type["type"],
                "description": f"{column_name.replace('_', ' ').title()}"
            }
            
            # Add format or enum constraints
            if "format" in column_type:
                property_def["format"] = column_type["format"]
            if "enum" in column_type:
                property_def["enum"] = column_type["enum"]
            
            properties[column_name] = property_def
            
            # Check if required
            if not column.nullable and not column.default and not column.server_default:
                required_fields.append(column_name)
        
        # Add dynamic fields for this model
        dynamic_fields = self._get_dynamic_fields_for_model(model_name)
        for field_def in dynamic_fields:
            field_schema = self._dynamic_field_to_schema(field_def)
            properties[field_def.field_name] = field_schema
            if field_def.is_required:
                required_fields.append(field_def.field_name)
        
        return {
            "name": f"create_{table_name.rstrip('s')}",
            "description": f"Create a new {model_name}",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required_fields
            }
        }
    
    def _generate_update_tool(self, model_class: Type) -> Dict[str, Any]:
        """Generate an update tool for a specific model"""
        model_name = model_class.__name__
        table_name = model_class.__tablename__
        
        # Similar to create tool but with ID required and other fields optional
        inspector = inspect(model_class)
        properties = {
            "id": {
                "type": "integer",
                "description": f"ID of the {model_name} to update"
            }
        }
        
        for column in inspector.columns:
            column_name = column.name
            
            # Skip internal fields and ID (already added)
            if column_name in ['id', 'created_at', 'updated_at', 'created_by']:
                continue
            
            column_type = self._sqlalchemy_to_json_type(column.type)
            property_def = {
                "type": column_type["type"],
                "description": f"Updated {column_name.replace('_', ' ').title()}"
            }
            
            if "format" in column_type:
                property_def["format"] = column_type["format"]
            if "enum" in column_type:
                property_def["enum"] = column_type["enum"]
            
            properties[column_name] = property_def
        
        # Add dynamic fields
        dynamic_fields = self._get_dynamic_fields_for_model(model_name)
        for field_def in dynamic_fields:
            field_schema = self._dynamic_field_to_schema(field_def)
            properties[field_def.field_name] = field_schema
        
        return {
            "name": f"update_{table_name.rstrip('s')}",
            "description": f"Update an existing {model_name}",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": ["id"]
            }
        }
    
    def _generate_dynamic_field_tools(self) -> List[Dict[str, Any]]:
        """Generate tools for managing dynamic fields"""
        return [
            {
                "name": "add_dynamic_field",
                "description": "Add a new dynamic field to any model (Event, TicketType, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_model": {
                            "type": "string",
                            "enum": ["Event", "TicketType", "Child", "User"],
                            "description": "Which model to add the field to"
                        },
                        "field_name": {
                            "type": "string",
                            "description": "Name of the new field (e.g., 'staff_id_number')"
                        },
                        "field_type": {
                            "type": "string",
                            "enum": ["string", "integer", "decimal", "boolean", "json", "date"],
                            "description": "Data type of the field"
                        },
                        "field_label": {
                            "type": "string",
                            "description": "Human-readable label for the field"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of what this field is for"
                        },
                        "is_required": {
                            "type": "boolean",
                            "description": "Whether this field is required"
                        },
                        "default_value": {
                            "type": "string",
                            "description": "Default value for the field"
                        },
                        "validation_rules": {
                            "type": "object",
                            "description": "Validation rules (min, max, pattern, etc.)"
                        }
                    },
                    "required": ["target_model", "field_name", "field_type", "field_label"]
                }
            },
            {
                "name": "set_dynamic_field_value",
                "description": "Set a value for a dynamic field on a specific record",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_model": {
                            "type": "string",
                            "enum": ["Event", "TicketType", "Child", "User"],
                            "description": "Model type"
                        },
                        "record_id": {
                            "type": "integer",
                            "description": "ID of the record to update"
                        },
                        "field_name": {
                            "type": "string",
                            "description": "Name of the dynamic field"
                        },
                        "value": {
                            "description": "Value to set (type depends on field definition)"
                        }
                    },
                    "required": ["target_model", "record_id", "field_name", "value"]
                }
            },
            {
                "name": "get_dynamic_fields",
                "description": "Get all dynamic fields available for a model",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_model": {
                            "type": "string",
                            "enum": ["Event", "TicketType", "Child", "User"],
                            "description": "Model to get dynamic fields for"
                        }
                    },
                    "required": ["target_model"]
                }
            }
        ]
    
    def _get_dynamic_fields_for_model(self, model_name: str) -> List[DynamicFieldDefinition]:
        """Get all active dynamic fields for a specific model"""
        return self.db.query(DynamicFieldDefinition).filter(
            DynamicFieldDefinition.target_model == model_name,
            DynamicFieldDefinition.is_active == True
        ).all()
    
    def _dynamic_field_to_schema(self, field_def: DynamicFieldDefinition) -> Dict[str, Any]:
        """Convert a dynamic field definition to JSON schema"""
        schema = {
            "description": field_def.description or field_def.field_label
        }
        
        # Map field types to JSON schema types
        type_mapping = {
            "string": "string",
            "integer": "integer",
            "decimal": "number",
            "boolean": "boolean",
            "json": "object",
            "date": "string"
        }
        
        schema["type"] = type_mapping.get(field_def.field_type, "string")
        
        if field_def.field_type == "date":
            schema["format"] = "date-time"
        
        if field_def.options:
            schema["enum"] = field_def.options
        
        return schema
    
    def _sqlalchemy_to_json_type(self, column_type) -> Dict[str, Any]:
        """Convert SQLAlchemy column type to JSON schema type"""
        type_name = str(column_type).lower()
        
        if "varchar" in type_name or "text" in type_name or "string" in type_name:
            return {"type": "string"}
        elif "integer" in type_name:
            return {"type": "integer"}
        elif "numeric" in type_name or "decimal" in type_name or "float" in type_name:
            return {"type": "number"}
        elif "boolean" in type_name:
            return {"type": "boolean"}
        elif "datetime" in type_name or "timestamp" in type_name:
            return {"type": "string", "format": "date-time"}
        elif "date" in type_name:
            return {"type": "string", "format": "date"}
        elif "json" in type_name:
            return {"type": "object"}
        elif "enum" in type_name:
            # Extract enum values if possible
            return {"type": "string"}
        else:
            return {"type": "string"}

class DynamicToolExecutor:
    """Execute dynamically generated tools"""
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)
    
    async def execute_dynamic_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a dynamically generated tool"""
        try:
            if tool_name == "add_dynamic_field":
                return await self._add_dynamic_field(**arguments)
            elif tool_name == "set_dynamic_field_value":
                return await self._set_dynamic_field_value(**arguments)
            elif tool_name == "get_dynamic_fields":
                return await self._get_dynamic_fields(**arguments)
            elif tool_name.startswith("create_"):
                return await self._create_record(tool_name, arguments)
            elif tool_name.startswith("update_"):
                return await self._update_record(tool_name, arguments)
            else:
                return {"error": f"Unknown dynamic tool: {tool_name}"}
        
        except Exception as e:
            self.logger.error(f"Error executing dynamic tool {tool_name}: {e}")
            return {"error": f"Tool execution failed: {str(e)}"}
    
    async def _add_dynamic_field(self, **kwargs) -> Dict[str, Any]:
        """Add a new dynamic field definition"""
        field_def = DynamicFieldDefinition(
            target_model=kwargs["target_model"],
            field_name=kwargs["field_name"],
            field_type=kwargs["field_type"],
            field_label=kwargs["field_label"],
            description=kwargs.get("description"),
            is_required=kwargs.get("is_required", False),
            default_value=kwargs.get("default_value"),
            validation_rules=kwargs.get("validation_rules"),
            created_by=self.user_id
        )
        
        self.db.add(field_def)
        self.db.commit()
        
        return {
            "success": True,
            "message": f"Dynamic field '{kwargs['field_name']}' added to {kwargs['target_model']}",
            "field_id": field_def.id
        }
    
    async def _set_dynamic_field_value(self, **kwargs) -> Dict[str, Any]:
        """Set a dynamic field value"""
        # This would use the mixin method we created
        model_class = self._get_model_class(kwargs["target_model"])
        if not model_class:
            return {"error": f"Unknown model: {kwargs['target_model']}"}
        
        record = self.db.query(model_class).filter(model_class.id == kwargs["record_id"]).first()
        if not record:
            return {"error": f"Record not found: {kwargs['record_id']}"}
        
        # Set the dynamic field (assuming we add the mixin to models)
        if hasattr(record, 'set_dynamic_field'):
            record.set_dynamic_field(kwargs["field_name"], kwargs["value"])
            return {
                "success": True,
                "message": f"Set {kwargs['field_name']} = {kwargs['value']} on {kwargs['target_model']} {kwargs['record_id']}"
            }
        else:
            return {"error": "Model does not support dynamic fields"}
    
    async def _get_dynamic_fields(self, **kwargs) -> Dict[str, Any]:
        """Get dynamic fields for a model"""
        fields = self.db.query(DynamicFieldDefinition).filter(
            DynamicFieldDefinition.target_model == kwargs["target_model"],
            DynamicFieldDefinition.is_active == True
        ).all()
        
        field_data = []
        for field in fields:
            field_data.append({
                "field_name": field.field_name,
                "field_type": field.field_type,
                "field_label": field.field_label,
                "description": field.description,
                "is_required": field.is_required,
                "options": field.options,
                "validation_rules": field.validation_rules
            })
        
        return {
            "success": True,
            "fields": field_data,
            "count": len(field_data)
        }
    
    async def _create_record(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record using dynamic schema"""
        model_name = tool_name.replace("create_", "").title()
        model_class = self._get_model_class(model_name)
        
        if not model_class:
            return {"error": f"Unknown model for tool: {tool_name}"}
        
        # Create record with standard fields
        record_data = {}
        dynamic_data = {}
        
        # Separate standard fields from dynamic fields
        inspector = inspect(model_class)
        standard_columns = [col.name for col in inspector.columns]
        
        for key, value in arguments.items():
            if key in standard_columns:
                record_data[key] = value
            else:
                dynamic_data[key] = value
        
        # Create the record
        record = model_class(**record_data)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        
        # Set dynamic fields if any
        for field_name, value in dynamic_data.items():
            if hasattr(record, 'set_dynamic_field'):
                record.set_dynamic_field(field_name, value)
        
        return {
            "success": True,
            "message": f"Created {model_name} with ID {record.id}",
            "record_id": record.id
        }
    
    async def _update_record(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Update a record using dynamic schema"""
        model_name = tool_name.replace("update_", "").title()
        model_class = self._get_model_class(model_name)
        
        if not model_class:
            return {"error": f"Unknown model for tool: {tool_name}"}
        
        record_id = arguments.pop("id")
        record = self.db.query(model_class).filter(model_class.id == record_id).first()
        
        if not record:
            return {"error": f"Record not found: {record_id}"}
        
        # Update standard and dynamic fields
        inspector = inspect(model_class)
        standard_columns = [col.name for col in inspector.columns]
        
        for key, value in arguments.items():
            if key in standard_columns:
                setattr(record, key, value)
            else:
                # Dynamic field
                if hasattr(record, 'set_dynamic_field'):
                    record.set_dynamic_field(key, value)
        
        self.db.commit()
        
        return {
            "success": True,
            "message": f"Updated {model_name} {record_id}"
        }
    
    def _get_model_class(self, model_name: str) -> Optional[Type]:
        """Get model class by name"""
        model_mapping = {
            "Event": Event,
            "TicketType": TicketType,
            "User": User,
            # Add more as needed
        }
        return model_mapping.get(model_name) 