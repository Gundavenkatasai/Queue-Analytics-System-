<?php

namespace MongoDB\BSON;

if (!class_exists(ObjectId::class)) {
    class ObjectId
    {
        public function __construct(string $id)
        {
        }
    }
}
